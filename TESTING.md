# Guía de Testing - Causal Narrative Engine

Este documento explica cómo ejecutar los diferentes tipos de tests y cuáles requieren API keys.

---

## Resumen Rápido

| Test Suite | Requiere API Key | Costo | Comando |
|------------|------------------|-------|---------|
| **Fase 1** (Core Engine) | ❌ No | Gratis | `pytest tests/test_fase1.py -v` |
| **MockAdapter** | ❌ No | Gratis | `pytest tests/test_mock_adapter.py -v` |
| **Fase 3 Integration** | ❌ No | Gratis | `pytest tests/test_fase3.py -v` |
| **OllamaAdapter** | ❌ No (local) | Gratis | Ver seccion Ollama abajo |
| **AnthropicAdapter** | ✅ Sí | ~$0.01 | `pytest -m anthropic_api -v` |

---

## Tests SIN API Key (Gratis, Rápidos)

Estos tests usan **MockAdapter** — un adapter determinista que NO se conecta a ninguna API.

### ✅ Fase 1: Core Engine

```bash
# Solo tests de Fase 1
pytest tests/test_fase1.py -v

# Con coverage
pytest tests/test_fase1.py --cov=cne_core -v
```

**Qué testea:**
- CausalValidator (detección de ciclos DAG)
- DramaticEngine (umbrales, eventos forzados)
- StateMachine (commits, branches, versionado)
- Propiedades P1-P4 (Causalidad, Determinismo, Versionado, Consistencia)

### ✅ MockAdapter Tests

```bash
pytest tests/test_mock_adapter.py -v
```

**Qué testea:**
- Generación determinista de narrativas
- Manejo de decisiones del jugador
- Eventos forzados
- Estadísticas del adapter
- Modo error (para testing de validación)

### ✅ Fase 3: Integration Tests

```bash
pytest tests/test_fase3.py -v
```

**Qué testea:**
- Flujo narrativo completo con MockAdapter
- Decisiones del jugador
- Eventos forzados por umbrales
- Validación de deltas dramáticos
- Generación de choices

### 🚀 Ejecutar todos los tests (sin API)

```bash
# Todos los tests que NO requieren API key
pytest tests/test_fase1.py tests/test_mock_adapter.py tests/test_fase3.py -v

# Más corto
pytest -v
```

---

## Tests con Ollama (Gratis, requiere Ollama instalado)

Estos tests usan **OllamaAdapter** — ejecuta LLMs localmente sin API keys ni costos.

### Requisitos

```bash
# 1. Instalar Ollama: https://ollama.com
# 2. Descargar modelo
ollama pull gemma3:4b

# 3. Verificar que Ollama esta corriendo
curl http://localhost:11434/api/tags
```

### Test manual

```python
python -c "
import asyncio
from adapters.ollama_adapter import OllamaAdapter
from cne_core import WorldDefinition, NarrativeTone, Entity, EntityType
from cne_core.interfaces.ai_adapter import NarrativeContext

async def test():
    adapter = OllamaAdapter(model='gemma3:4b')
    hero = Entity(name='Kael', entity_type=EntityType.CHARACTER, attributes={'health': 100})
    world = WorldDefinition(
        name='Test', context='Medieval fantasy', protagonist='Kael',
        era='Medieval', tone=NarrativeTone.DARK, initial_entities=[hero],
    )
    ctx = NarrativeContext(
        world_definition=world, current_depth=0,
        current_dramatic_state={'tension':30,'hope':60,'chaos':20,'rhythm':50,'saturation':0,'connection':40,'mystery':50},
        current_entity_states={}, current_world_vars={}, commit_chain=[],
    )
    result = await adapter.generate_narrative(ctx)
    print('Narrativa:', result.narrative_text[:200])
    print('Opciones:', [c.text for c in result.choices])
    print('[OK] OllamaAdapter funciona!')

asyncio.run(test())
"
```

### Test via API REST

```bash
# 1. Levantar servidor
uvicorn api.main:app --reload

# 2. Crear mundo
curl -X POST http://localhost:8000/worlds \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "context": "Fantasy", "protagonist": "Hero", "era": "Medieval", "tone": "dark"}'

# 3. Iniciar narrativa con Ollama
curl -X POST http://localhost:8000/worlds/{world_id}/start \
  -H "Content-Type: application/json" \
  -d '{"adapter_type": "ollama"}'
```

### Modelos recomendados

| Modelo | RAM | Notas |
|--------|-----|-------|
| `gemma3:4b` (default) | ~3GB | Buen balance calidad/velocidad |
| `qwen3:4b` | ~3GB | Muy bueno siguiendo instrucciones JSON |
| `llama3.2:3b` | ~2GB | Intermedio, mas ligero |
| `mistral:7b` | ~4GB | Mejor calidad, requiere mas RAM |

---

## Tests CON API Key (Cuestan dinero)

Estos tests se conectan a la **API real de Anthropic (Claude)** y consumen tokens.

### ⚠️ Configuración requerida

1. **Copia el archivo de ejemplo:**
   ```bash
   cp .env.example .env
   ```

2. **Edita `.env` y agrega tu API key:**
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-tu-key-real-aquí
   ```

3. **Obtén tu API key en:**
   https://console.anthropic.com/settings/keys

### ✅ AnthropicAdapter Tests

```bash
# Ejecutar SOLO los tests que usan API real
pytest -m anthropic_api -v

# Con más detalle
pytest tests/test_anthropic_adapter.py -v --tb=short
```

**Qué testea:**
- Generación real con Claude
- Respuesta a decisiones del jugador
- Validación de respuestas de IA
- Tracking de estadísticas (tokens, calls, etc.)

**Costo estimado:** ~$0.01 USD por ejecución completa

### 🛡️ Protección contra ejecución accidental

Los tests con `@pytest.mark.anthropic_api` se **saltan automáticamente** si:
- No tienes `ANTHROPIC_API_KEY` configurada
- La key es el valor de ejemplo de `.env.example`

Mensaje de skip:
```
SKIPPED - ANTHROPIC_API_KEY no esta configurada.
```

---

## Comandos útiles

### Ejecutar tests específicos

```bash
# Un solo test
pytest tests/test_fase1.py::test_causal_validator -v

# Un solo archivo
pytest tests/test_mock_adapter.py -v

# Por marker
pytest -m fase1 -v
pytest -m fase3 -v
```

### Coverage

```bash
# Coverage completo
pytest --cov=cne_core --cov=adapters --cov-report=html -v

# Solo para un módulo
pytest tests/test_mock_adapter.py --cov=adapters.mock_adapter -v

# Abrir reporte HTML
start htmlcov/index.html  # Windows
open htmlcov/index.html   # macOS/Linux
```

### Excluir tests con API

```bash
# Ejecutar TODO excepto tests que requieren API
pytest -m "not anthropic_api" -v
```

---

## Markers disponibles

```bash
pytest -m fase1 -v          # Solo Fase 1
pytest -m fase2 -v          # Solo Fase 2 (PostgreSQL)
pytest -m fase3 -v          # Solo Fase 3
pytest -m anthropic_api -v  # Solo tests con API real
pytest -m integration -v    # Tests de integración
```

---

## Estrategia Recomendada

### Durante desarrollo (día a día)

```bash
# Rápido, gratis, sin API
pytest tests/test_fase1.py tests/test_mock_adapter.py tests/test_fase3.py -v
```

### Antes de hacer commit

```bash
# Todos los tests sin API + coverage
pytest --cov=cne_core --cov=adapters -v
```

### Antes de release

```bash
# TODO incluyendo API real
pytest -v
```

### En CI/CD (GitHub Actions, etc.)

```bash
# Solo tests sin API (para evitar costos)
pytest -m "not anthropic_api" -v --cov=cne_core --cov=adapters
```

---

## Troubleshooting

### ❌ "ImportError: cannot import name 'AsyncAnthropic'"

**Solución:**
```bash
pip install anthropic
```

### ❌ "ANTHROPIC_API_KEY no esta configurada"

**Solución:**
1. Verifica que `.env` existe
2. Verifica que contiene `ANTHROPIC_API_KEY=sk-ant-...`
3. Verifica que la key no es el ejemplo

### ❌ "ValidationError: 1 validation error for DramaticDeltaDict"

**Solución:**
```bash
pip install --upgrade pydantic
```

### ❌ Tests lentos

**Solución:**
```bash
# Ejecutar en paralelo (requiere pytest-xdist)
pip install pytest-xdist
pytest -n auto -v
```

---

## Estructura de Tests

```
tests/
├── test_fase1.py              # Core Engine (gratis)
├── test_mock_adapter.py       # MockAdapter (gratis)
├── test_fase3.py              # Integration con Mock (gratis)
├── test_anthropic_adapter.py  # API real (cuesta dinero)
adapters/
└── ollama_adapter.py          # OllamaAdapter (test manual, gratis)
```

---

## Configuración en pyproject.toml

Los markers están definidos en:

```toml
[tool.pytest.ini_options]
markers = [
    "fase1: Tests de Fase 1 (Core Engine en memoria)",
    "fase2: Tests de Fase 2 (Persistencia con PostgreSQL)",
    "fase3: Tests de Fase 3 (AI Adapter)",
    "anthropic_api: Tests que requieren API key de Anthropic (consumen tokens)",
    "integration: Tests de integración (requieren servicios externos)",
]
```

---

## FAQ

**P: ¿Puedo desarrollar sin API key?**
R: Sí. Usa MockAdapter para todo. Es determinista y gratis.

**P: ¿Cuánto cuestan los tests de Anthropic?**
R: ~$0.01 USD por ejecución completa (4 tests). Cada test usa ~500-1000 tokens.

**P: ¿Puedo probar con IA gratis?**
R: Sí. Instala [Ollama](https://ollama.com), descarga `gemma3:4b`, y usa `adapter_type: "ollama"`. Corre localmente sin API key.

**P: ¿Qué modelo de Anthropic usa por defecto?**
R: `claude-3-5-sonnet-20241022` (balance calidad/precio)

**P: ¿Puedo usar otro modelo?**
R: Sí. Para Anthropic: edita `ANTHROPIC_MODEL` en `.env`. Para Ollama: edita `OLLAMA_MODEL` en `.env` o pasa `model=` al constructor.

**P: ¿Los tests de Anthropic se ejecutan automáticamente?**
R: No. Solo si ejecutas `pytest -m anthropic_api` explícitamente.

**P: ¿Cómo evito ejecutarlos por accidente?**
R: Usa `pytest -m "not anthropic_api"` o simplemente `pytest` (que los skipea si no hay API key).

---

## Próximos Pasos

- **Fase 4**: Tests de FastAPI (requieren servidor corriendo)
- **Fase 5**: Tests de integración completos (Mock + PostgreSQL + API)
- **Performance**: Tests de carga con múltiples narrativas concurrentes
