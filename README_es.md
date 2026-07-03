# Causal Narrative Engine (CNE)

**Motor narrativo independiente basado en causalidad formal para generar historias ramificadas con IA manteniendo coherencia verificable.**

---

## ¿Qué es CNE?

Un framework reutilizable que cualquier proyecto puede integrar — un juego, una herramienta de escritura, una API, o un pipeline de generación de contenido.

**La coherencia es propiedad estructural del motor, NO del LLM.**

```
┌──────────────────────────────────┐
│  IA propone eventos              │
│         ↓                        │
│  Motor valida coherencia causal  │
│         ↓                        │
│  Motor decide qué pasa           │
└──────────────────────────────────┘
```

---

## Estado actual

| Fase | Estado | Descripción |
|------|--------|-------------|
| **Fase 1** | ✅ **COMPLETADA** | Core Engine en memoria (sin dependencias) |
| **Fase 2** | ✅ **COMPLETADA** | Persistencia con PostgreSQL + SQLAlchemy async |
| **Fase 3** | ✅ **COMPLETADA** | AI Adapter (Anthropic + Ollama + Mock) |
| **Fase 4** | ✅ **COMPLETADA** | FastAPI REST API |
| **Fase 5** | 🔲 Pendiente | Release público en PyPI |

---

## Quickstart — Solo Core Engine (sin dependencias)

```bash
# Instalar solo el core (cero dependencias externas)
pip install -e .

# Verificar
python -c "import cne_core; print(cne_core.__version__)"

# Ejecutar tests del core
python tests/test_fase1.py

# Ejecutar ejemplo mínimo
python docs/examples/minimal_example.py
```

## Quickstart — Con PostgreSQL + API REST

```bash
# 1. Instalar todas las dependencias
pip install -e ".[all]"

# 2. Levantar PostgreSQL
docker-compose up -d

# 3. Crear tablas
alembic upgrade head

# 4. Ejecutar ejemplo
python examples/fase2_example.py

# 5. Levantar API REST
uvicorn api.main:app --reload

# 6. Ejecutar tests
pytest tests/ -v
```

---

## Conceptos Core

### 1. Modelo Formal

```
CNE = (W, E, S, D, T, C, Φ)
```

- **W** = WorldDefinition (semilla inmutable)
- **E** = Espacio de eventos narrativos
- **S(t)** = Estado del mundo en tiempo t
- **D(t)** = Vector Dramatico de 7 medidores
- **T** = Funcion de transicion (IA propone -> motor valida)
- **C** = Grafo causal (DAG sin ciclos)
- **Φ** = Evaluador dramatico (umbrales -> eventos forzados)

**4 garantias:**
- ✅ **Causalidad**: El grafo es siempre un DAG valido
- ✅ **Determinismo**: El estado es reconstruible desde snapshots
- ✅ **Versionado**: Tipo Git, puedes volver atras en decisiones
- ✅ **Consistencia**: Entidades muertas no actuan, variables en rango

### 2. Sistema Dramatico Multi-Medidor (SDMM)

7 medidores independientes en vez de un solo indicador:

| Medidor | Qué mide |
|---------|----------|
| `tension` | Nivel de conflicto activo |
| `hope` | Percepcion de que las cosas pueden mejorar |
| `chaos` | Entropia del mundo |
| `rhythm` | Velocidad narrativa |
| `saturation` | Agotamiento del arco actual |
| `connection` | Vinculo emocional con personajes |
| `mystery` | Preguntas sin resolver |

**Umbrales -> Eventos Forzados:**
```
tension > 85        ->  CLIMAX forzado
hope < 10           ->  TRAGEDIA forzada
saturation > 95     ->  CIERRE DE ARCO forzado
mystery + tension > 130  ->  REVELACION CLIMATICA
```

### 3. Arquitectura Independiente

```
┌────────────────────────────────┐
│  Cualquier cliente externo     │
│  (juego, web, CLI...)          │
└───────────┬────────────────────┘
            │ import cne_core / HTTP
┌───────────▼────────────────────┐
│  FastAPI REST API         ✅   │
└───────────┬────────────────────┘
            │
┌───────────▼────────────────────┐
│     Core Engine                │
│  CausalValidator │ DramaticEngine
│  StateMachine    │ NarrativeRunner
└────┬──────────────────┬────────┘
     │                  │
┌────▼─────────┐  ┌────▼─────────┐
│ Persistence  │  │ AI Adapter   │
│              │  │              │
│ Interface    │  │ Interface    │
│ ─────────    │  │ ─────────    │
│ PostgreSQL ✅│  │ Anthropic ✅ │
│ InMemory ✅  │  │ Ollama ✅    │
└──────────────┘  │ Mock ✅      │
                  └──────────────┘
```

---

## Instalacion

### Solo Core Engine (sin dependencias externas)

```bash
pip install -e .
```

**Solo Python 3.11+ stdlib** — tests sin PostgreSQL, sin API keys, sin Docker.

### Con PostgreSQL

```bash
pip install -e ".[persistence,dev]"
docker-compose up -d
alembic upgrade head
```

### Con IA local (Ollama — gratis, sin API key)

```bash
pip install -e ".[ai,persistence,dev]"

# Instalar Ollama: https://ollama.com
# Descargar modelo (3GB):
ollama pull gemma3:4b
```

### Con IA cloud (Anthropic)

```bash
pip install -e ".[ai,persistence,dev]"
export ANTHROPIC_API_KEY="sk-..."
```

### Todo junto

```bash
pip install -e ".[all]"
```

---

## Uso programatico

### Ejemplo basico (Core Engine en memoria)

```python
from cne_core import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core import StateMachine, NarrativeChoice, DramaticDelta

# 1. Crear mundo
hero = Entity(
    name="Aldric",
    entity_type=EntityType.CHARACTER,
    attributes={"health": 100, "courage": 80}
)

world = WorldDefinition(
    name="El Reino de las Sombras",
    context="Un reino medieval donde la magia oscura amenaza...",
    protagonist="Aldric, un caballero desterrado",
    era="Medieval fantastico",
    tone=NarrativeTone.DARK,
    initial_entities=[hero]
)

# 2. Iniciar motor
engine = StateMachine(world)

# 3. Comenzar historia
result = engine.start(
    initial_narrative="El reino esta en peligro...",
    initial_choices=[
        NarrativeChoice(text="Ir al palacio"),
        NarrativeChoice(text="Huir a las montanas"),
    ]
)

# 4. Avanzar historia
result = engine.advance_story(
    choice_text="Ir al palacio",
    narrative_text="Aldric cabalga hacia la capital...",
    summary="Aldric acepta la mision.",
    choices=[NarrativeChoice(text="Entrar por la puerta principal")],
    dramatic_delta=DramaticDelta(tension=10, hope=-5)
)

print(result.display())
```

### Con PostgreSQL

```python
import asyncio
from persistence.database import DatabaseConfig
from persistence.repositories.postgresql_repository import PostgreSQLRepository

async def main():
    db_config = DatabaseConfig(
        "postgresql+asyncpg://cne_user:cne_password_dev@localhost:5432/cne_db"
    )
    repo = PostgreSQLRepository(db_config)
    await repo.save_world(world)
    await repo.save_commit(commit)
    trunk = await repo.get_trunk(commit.id)

asyncio.run(main())
```

---

## API REST

Levantar el servidor:
```bash
uvicorn api.main:app --reload --port 8000
```

### Endpoints principales

| Metodo | Endpoint | Descripcion |
|--------|----------|-------------|
| `POST` | `/worlds` | Crear WorldDefinition |
| `GET` | `/worlds/{world_id}` | Obtener mundo |
| `POST` | `/worlds/{world_id}/start` | Iniciar historia |
| `POST` | `/commits/{commit_id}/advance` | Tomar decision |
| `GET` | `/commits/{commit_id}` | Estado de un commit |
| `GET` | `/commits/{commit_id}/dramatic` | Vector dramatico |
| `GET` | `/health` | Estado del servidor |

Documentacion interactiva en `http://localhost:8000/docs` (Swagger UI).

---

## Integracion

Para conectar tu propio sistema de persistencia o tu propio LLM al motor, consulta la **[Guia de Integracion](docs/integration_guide.md)**.

Cubre:
- Como implementar `NarrativeRepository` (tu base de datos)
- Como implementar `AIAdapter` (tu LLM)
- Uso directo del SDK Python
- Uso via API REST

---

## Tests

```bash
# Core Engine en memoria (sin dependencias)
python tests/test_fase1.py

# Adapters + integracion con engine (sin API key)
pytest tests/test_adapters.py -v

# API REST (requiere Docker + PostgreSQL)
pytest tests/test_api.py -v

# Persistencia (requiere Docker + PostgreSQL)
pytest tests/test_persistence_integration.py -v

# Todos los tests
pytest tests/ -v
```

---

## Estructura del proyecto

```
cne_core/                          # Core Engine
├── models/                        # Dataclasses (WorldDefinition, NarrativeEvent, EntityCreation, etc.)
├── engine/                        # CausalValidator, DramaticEngine, StateMachine
├── interfaces/                    # Contratos abstractos (NarrativeRepository, AIAdapter)
└── ai/                            # ContextBuilder, ResponseValidator, ResponseSchema

adapters/                          # Implementaciones de AIAdapter
├── mock_adapter.py                # Mock para tests (determinista)
├── anthropic_adapter.py           # Anthropic Claude
└── ollama_adapter.py              # Ollama (LLMs locales gratuitos)

persistence/                       # Persistencia PostgreSQL
├── database.py                    # Config SQLAlchemy 2.0 async
├── models/                        # ORM models (WorldORM, EventORM, CommitORM, EntityCreationORM)
├── repositories/                  # PostgreSQLRepository
└── queries/                       # CTEs recursivas (validacion causal en SQL)

api/                               # FastAPI REST API
├── routers/                       # Endpoints (worlds, narrative, health)
├── services/                      # NarrativeServiceV2
├── models/                        # Request/Response schemas (Pydantic)
└── dependencies.py                # Inyeccion de dependencias

cli/                               # CLI interactivo
migrations/                        # Alembic (4 migraciones)
tests/                             # Tests (test_fase1, test_adapters, test_api, test_persistence_integration)
docs/                              # Documentacion
web/                               # Interfaz web (en desarrollo)
```

---

## Roadmap

### ✅ Fase 1 — Core Engine
- [x] Dataclasses del dominio
- [x] CausalValidator (DAG sin ciclos)
- [x] DramaticEngine (SDMM)
- [x] StateMachine (orquestador en memoria)
- [x] Tests completos

### ✅ Fase 2 — Persistencia
- [x] Interfaces abstractas (Repository pattern)
- [x] ORM models (SQLAlchemy 2.0 async)
- [x] PostgreSQLRepository
- [x] CTEs recursivas (validacion causal en SQL)
- [x] Migraciones (Alembic)
- [x] Docker Compose

### ✅ Fase 3 — AI Adapter
- [x] AnthropicAdapter (Claude)
- [x] OllamaAdapter (LLMs locales gratuitos)
- [x] MockAIAdapter (tests sin API key)
- [x] ContextBuilder (tronco activo)
- [x] ResponseValidator (validar JSON)

### ✅ Fase 4 — API REST
- [x] FastAPI endpoints
- [x] NarrativeServiceV2 con persistencia
- [x] Choices persistidas en BD
- [x] Engine reconstruction desde BD
- [x] Entity creation dinamica (personajes, items, artefactos en runtime)
- [x] Dockerfile + Docker Compose con Ollama

### 🔲 Fase 5 — Release
- [ ] PyPI release (`pip install cne-core`)
- [ ] Docker image publico
- [ ] Documentacion completa

### 🔲 Fase 6 — Paper Academico
- [ ] Draft inicial
- [ ] Experimentos y metricas formales
- [ ] Submit a AIIDE / IEEE CoG

---

## Licencia

MIT — Ver [LICENSE](LICENSE) para detalles.

---

## Contacto

- **Repositorio**: [github.com/Squisix/causal_narrative_engine](https://github.com/Squisix/causal_narrative_engine)
- **Issues**: [Reportar un problema](https://github.com/Squisix/causal_narrative_engine/issues)
- **Autor**: Marco Guerrero (mvsquisix@gmail.com)
