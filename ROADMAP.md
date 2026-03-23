# Roadmap - Causal Narrative Engine

## Estado Actual: FASE 2 COMPLETADA ✅

---

## ✅ FASE 1 - Core Engine (COMPLETADA)
**Objetivo:** Motor narrativo funcional en memoria.

- [x] Modelos de dominio (WorldDefinition, Entity, NarrativeEvent, NarrativeCommit)
- [x] CausalValidator (detección de ciclos DAG con BFS)
- [x] DramaticEngine (SDMM completo con 7 medidores + umbrales)
- [x] StateMachine (orquestador central)
- [x] Tests completos (test_fase1.py passing)

**Tests:** 3/3 passing (100%)

---

## ✅ FASE 2 - Persistencia PostgreSQL (COMPLETADA)
**Objetivo:** Persistir todo el estado en PostgreSQL con SQLAlchemy async.

- [x] DatabaseConfig (SQLAlchemy 2.0 async)
- [x] ORM Models (WorldORM, EntityORM, EventORM, CommitORM)
- [x] PostgreSQLRepository (26 métodos implementados)
- [x] Migraciones Alembic (001_initial_schema.py)
- [x] CausalQueries (CTEs recursivas en SQL)
- [x] StateRebuilder (reconstrucción de estado desde deltas)
- [x] Docker Compose (PostgreSQL + Redis + Adminer)
- [x] Tests completos (test_fase2.py passing)

**Tests:** 6/6 passing (100%)
**Cobertura:** 57% global, 68% en PostgreSQLRepository

---

## 🔲 FASE 3 - AI Adapter (SIGUIENTE - EN PROGRESO)
**Objetivo:** Integrar con Anthropic API para generar narrativa automáticamente.

### Tareas pendientes:

#### 3.1 Contrato JSON de respuesta
- [ ] Definir schema Pydantic para respuesta de la IA
- [ ] Validar que contenga: narrative, summary, choices, deltas, causal_reason
- [ ] Manejo de errores si la IA retorna JSON inválido

#### 3.2 Context Builder
- [ ] Implementar `build_context_for_ai()` que genere el prompt completo
- [ ] Incluir: semilla del mundo, tronco activo, estado dramático, constraint forzado
- [ ] Optimizar tokens (max ~2000 tokens de contexto)
- [ ] Comprimir capítulos antiguos a 1 línea cada uno

#### 3.3 Anthropic Adapter
- [ ] `AnthropicAdapter` implementando `AIAdapter` interface
- [ ] Usar Anthropic SDK con modelo Claude 3.5 Sonnet
- [ ] System prompt que explique el contrato y las reglas
- [ ] Manejo de rate limiting y errores de API
- [ ] Retry logic con exponential backoff

#### 3.4 Response Validator
- [ ] Validar que los deltas no violen propiedades (P1-P4)
- [ ] Verificar que entidades muertas no actúen
- [ ] Validar que dramatic_deltas estén en rango [-100, +100]
- [ ] Logging detallado de validaciones fallidas

#### 3.5 Integration Layer
- [ ] `AsyncStateMachine` que usa `AIAdapter` + `PostgreSQLRepository`
- [ ] `advance_with_ai(commit_id, choice_text)` → genera narrativa automáticamente
- [ ] Manejo transaccional: si falla validación, rollback completo

#### 3.6 Tests
- [ ] `test_anthropic_adapter.py` - test con API real (requiere API key)
- [ ] `test_mock_ai_adapter.py` - test con mock (sin API key)
- [ ] `test_context_builder.py` - verificar que el prompt sea correcto
- [ ] `test_response_validator.py` - validaciones de seguridad

### Archivos a crear:
```
cne_core/
├── ai/
│   ├── __init__.py
│   ├── context_builder.py       # Construye el prompt para la IA
│   ├── response_schema.py       # Schema Pydantic de respuesta
│   └── response_validator.py    # Valida respuesta de IA
adapters/
├── __init__.py
├── anthropic_adapter.py         # Implementación con Anthropic SDK
├── openai_adapter.py            # (opcional) Implementación con OpenAI
└── mock_adapter.py              # Para tests sin API key
tests/
├── test_context_builder.py
├── test_anthropic_adapter.py
└── test_mock_adapter.py
```

### Configuración necesaria:
```bash
# Instalar Anthropic SDK
pip install anthropic

# Variable de entorno
export ANTHROPIC_API_KEY="sk-ant-..."

# O en .env
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
```

### Ejemplo de uso esperado:
```python
from cne_core import AsyncStateMachine
from adapters import AnthropicAdapter
from persistence.repositories import PostgreSQLRepository

# Setup
repo = PostgreSQLRepository(db_config)
ai_adapter = AnthropicAdapter(api_key="sk-ant-...")
engine = AsyncStateMachine(world, repo, ai_adapter)

# Iniciar historia (IA genera el primer capítulo)
result = await engine.start()
print(result.narrative_text)  # Generado por Claude
print(result.available_choices)  # [Choice1, Choice2, Choice3]

# Avanzar (jugador elige, IA genera el siguiente capítulo)
result = await engine.advance_with_ai(
    commit_id=result.commit.id,
    choice_text="Ordenar una investigación secreta"
)
print(result.narrative_text)  # Nuevo capítulo generado por Claude
```

---

## 🔲 FASE 4 - FastAPI REST API
**Objetivo:** Exponer el motor como servicio HTTP consumible por cualquier cliente.

### Tareas:
- [ ] Endpoints RESTful (`/worlds`, `/commits`, `/branches`)
- [ ] WebSocket para narrativa en streaming
- [ ] Autenticación JWT
- [ ] Rate limiting
- [ ] Documentación OpenAPI automática
- [ ] Docker image del servicio
- [ ] Tests de integración con httpx

### Endpoints principales:
```
POST   /worlds                       # Crear semilla
GET    /worlds/{id}
POST   /worlds/{id}/start            # Iniciar historia
POST   /commits/{id}/advance         # Tomar decisión → IA genera
GET    /commits/{id}
GET    /commits/{id}/state
GET    /commits/{id}/dramatic_state
GET    /branches
POST   /commits/{id}/goto            # Navegación temporal
```

---

## 🔲 FASE 5 - Documentación y Release
**Objetivo:** Hacer el motor usable por desarrolladores externos.

### Tareas:
- [ ] README completo con ejemplos
- [ ] Quickstart guide (motor funcionando en < 10 minutos)
- [ ] API Reference (docs/ generados con mkdocs)
- [ ] Examples directory (minimal, with_postgres, with_claude)
- [ ] CONTRIBUTING.md
- [ ] Publicar en PyPI como `cne-core`
- [ ] GitHub release con changelog

---

## 🔲 FASE 6 - Paper Académico
**Objetivo:** Publicar el framework como investigación en narrativa computacional.

### Tareas:
- [ ] Formalización matemática completa del modelo
- [ ] Experimentos con diferentes géneros narrativos
- [ ] Métricas: CCS, ECR, DAF, TTR, CE (ver CLAUDE.md)
- [ ] Comparación con sistemas existentes (Ink, Twine, Storylets)
- [ ] Paper draft en LaTeX
- [ ] Submission a AIIDE o IEEE CoG

---

## Métricas de Progreso

| Fase | Estado | Tests | Cobertura | Notas |
|------|--------|-------|-----------|-------|
| 1 - Core Engine | ✅ COMPLETADA | 3/3 ✅ | ~95% | Motor funcional en memoria |
| 2 - Persistencia | ✅ COMPLETADA | 6/6 ✅ | 57% | PostgreSQL + CTEs recursivas |
| 3 - AI Adapter | 🔲 Pendiente | 0/6 | - | Integración con Anthropic |
| 4 - FastAPI | 🔲 Pendiente | - | - | REST API |
| 5 - Docs | 🔲 Pendiente | - | - | Documentación completa |
| 6 - Paper | 🔲 Pendiente | - | - | Publicación académica |

---

## Comandos útiles

```bash
# Fase 1 - Tests en memoria
python tests/test_fase1.py

# Fase 2 - Tests con PostgreSQL
docker-compose up -d
python -m alembic upgrade head
python -m pytest tests/test_fase2.py -v

# Verificar estado de Fase 2
python scripts/verify_fase2.py

# Ver cobertura HTML
python -m pytest tests/ --cov=cne_core --cov=persistence --cov-report=html
# Abrir: htmlcov/index.html
```
