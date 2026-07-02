# Guía de Testing - Causal Narrative Engine

Este documento explica cómo ejecutar los diferentes tipos de tests y cuáles requieren API keys.

---

## Resumen Rápido

| Test Suite | Requiere API Key | Requiere Docker | Comando |
|------------|------------------|-----------------|---------|
| **Core Engine** (test_fase1) | ❌ No | ❌ No | `pytest tests/test_fase1.py -v` |
| **Adapters** (test_adapters) | ❌ No | ❌ No | `pytest tests/test_adapters.py -v` |
| **API REST** (test_api) | ❌ No | ✅ Sí | `pytest tests/test_api.py -v` |
| **Persistencia** (test_persistence) | ❌ No | ✅ Sí | `pytest tests/test_persistence_integration.py -v` |
| **AnthropicAdapter** | ✅ Sí | ❌ No | `pytest tests/test_anthropic_adapter.py -v` |

---

## Tests SIN API Key ni Docker (Gratis, Rápidos)

### ✅ Core Engine (test_fase1.py)

```bash
pytest tests/test_fase1.py -v
```

**Qué testea:**
- CausalValidator (detección de ciclos DAG)
- DramaticEngine (umbrales, eventos forzados, SDMM)
- StateMachine (commits, branches, versionado)
- Propiedades P1-P4 (Causalidad, Determinismo, Versionado, Consistencia)

### ✅ Adapters (test_adapters.py)

```bash
pytest tests/test_adapters.py -v
```

**Qué testea:**
- MockAdapter: generación determinista, decisiones del jugador, eventos forzados, estadísticas, modo error
- Integración MockAdapter + StateMachine: flujo completo generate → process → state
- Entity creation dinámica: crear personajes y artifacts en runtime
- Entity creation + go_to_commit: entidades creadas después no aparecen al navegar atrás
- ResponseSchema: parseo de entity_creations y 5-tuple de to_core_models()

---

## Tests CON Docker (Requieren PostgreSQL)

Estos tests requieren PostgreSQL corriendo:

```bash
docker-compose up -d
alembic upgrade head
```

### ✅ API REST (test_api.py)

```bash
pytest tests/test_api.py -v
```

**Qué testea:**
- CRUD de mundos (crear, obtener, eliminar)
- Flujo narrativo completo (start → advance → advance)
- Navegación de commits (goto, list, existing_paths)
- Estado dramático por commit
- Causal reason en respuestas
- Custom choices del jugador

### ✅ Persistencia (test_persistence_integration.py)

```bash
pytest tests/test_persistence_integration.py -v
```

**Qué testea:**
- PostgreSQLRepository: save/get de worlds, commits, events
- Entity persistence y entity creation records
- Dramatic state snapshots y deltas

---

## Tests CON API Key (Cuestan dinero)

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

### ✅ AnthropicAdapter (test_anthropic_adapter.py)

```bash
pytest tests/test_anthropic_adapter.py -v
```

**Qué testea:**
- Generación real con Claude
- Respuesta a decisiones del jugador
- Validación de respuestas de IA
- Tracking de estadísticas (tokens, calls, etc.)

**Costo estimado:** ~$0.01 USD por ejecución completa

Los tests con `@pytest.mark.anthropic_api` se **saltan automáticamente** si no tienes `ANTHROPIC_API_KEY` configurada.

---

## Tests con Ollama (Gratis, requiere Ollama instalado)

OllamaAdapter se prueba manualmente ya que requiere un LLM local corriendo.

### Requisitos

```bash
# 1. Instalar Ollama: https://ollama.com
# 2. Descargar modelo
ollama pull gemma3:4b

# 3. Verificar que Ollama esta corriendo
curl http://localhost:11434/api/tags
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

## Estrategia Recomendada

### Durante desarrollo (día a día)

```bash
# Rápido, gratis, sin Docker
pytest tests/test_fase1.py tests/test_adapters.py -v
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

## Estructura de Tests

```
tests/
├── conftest.py                    # Fixtures compartidos (PostgreSQL session, etc.)
├── test_fase1.py                  # Core Engine en memoria (gratis, sin dependencias)
├── test_adapters.py               # MockAdapter + integracion engine + entity creation
├── test_api.py                    # API REST completa (requiere Docker)
├── test_persistence_integration.py # PostgreSQL repository (requiere Docker)
└── test_anthropic_adapter.py      # API real Anthropic (cuesta dinero, skip sin key)
```

---

## Comandos útiles

```bash
# Un solo test
pytest tests/test_adapters.py::test_basic_generation -v

# Un solo archivo
pytest tests/test_api.py -v

# Con coverage
pytest --cov=cne_core --cov=adapters --cov-report=html -v

# Excluir tests con API
pytest -m "not anthropic_api" -v

# Ejecutar en paralelo (requiere pytest-xdist)
pip install pytest-xdist
pytest -n auto -v
```

---

## Troubleshooting

### ❌ "ImportError: cannot import name 'AsyncAnthropic'"

```bash
pip install anthropic
```

### ❌ "ANTHROPIC_API_KEY no esta configurada"

1. Verifica que `.env` existe
2. Verifica que contiene `ANTHROPIC_API_KEY=sk-ant-...`
3. Verifica que la key no es el ejemplo

### ❌ Tests de API fallan con timeout

Los tests de API usan MockAdapter por defecto. Si fallan con timeout, verifica que PostgreSQL está corriendo:
```bash
docker-compose up -d
alembic upgrade head
```

### ❌ "ValidationError: 1 validation error for DramaticDeltaDict"

```bash
pip install --upgrade pydantic
```

---

## FAQ

**P: ¿Puedo desarrollar sin API key?**
R: Sí. Usa MockAdapter para todo. Es determinista y gratis.

**P: ¿Puedo probar con IA gratis?**
R: Sí. Instala [Ollama](https://ollama.com), descarga `gemma3:4b`, y usa `adapter_type: "ollama"`.

**P: ¿Los tests de Anthropic se ejecutan automáticamente?**
R: No. Se skipean si no hay API key configurada.

**P: ¿Qué modelo de Anthropic usa por defecto?**
R: Configurable via `ANTHROPIC_MODEL` en `.env`.

**P: ¿Puedo usar otro modelo de Ollama?**
R: Sí. Edita `OLLAMA_MODEL` en `.env` o pasa `model=` al constructor.
