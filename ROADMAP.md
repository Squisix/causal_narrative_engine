# Roadmap - Causal Narrative Engine

## Estado Actual: FASE 4 COMPLETADA ✅

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

## ✅ FASE 3 - AI Adapter (COMPLETADA)
**Objetivo:** Integrar con LLMs para generar narrativa automaticamente.

- [x] Schema Pydantic para respuesta de la IA (`response_schema.py`)
- [x] ContextBuilder (tronco activo, compresion de contexto)
- [x] AnthropicAdapter (Claude, requiere API key)
- [x] OllamaAdapter (LLMs locales gratuitos via Ollama)
- [x] MockAdapter (tests deterministas sin API key)
- [x] ResponseValidator (validar JSON de la IA)
- [x] Normalizacion de respuestas para modelos pequenos
- [x] Tests con MockAdapter y Anthropic

### Archivos:
```
cne_core/ai/
├── context_builder.py       # Construye el prompt para la IA
├── response_schema.py       # Schema Pydantic de respuesta
└── response_validator.py    # Valida respuesta de IA
adapters/
├── mock_adapter.py          # Para tests sin API key
├── anthropic_adapter.py     # Anthropic Claude (API key)
└── ollama_adapter.py        # Ollama (LLMs locales, gratis)
```

### Uso con Ollama (gratis):
```bash
ollama pull gemma3:4b
```
```python
from adapters import OllamaAdapter
adapter = OllamaAdapter(model="gemma3:4b")
result = await adapter.generate_narrative(ctx)
```

### Uso con Anthropic (API key):
```python
from adapters import AnthropicAdapter
adapter = AnthropicAdapter(api_key="sk-ant-...")
result = await adapter.generate_narrative(ctx)
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
| 3 - AI Adapter | ✅ COMPLETADA | ✅ | - | Anthropic + Ollama + Mock |
| 4 - FastAPI | ✅ COMPLETADA | ✅ | - | REST API |
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
