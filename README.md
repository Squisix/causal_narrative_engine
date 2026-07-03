# Causal Narrative Engine (CNE)

**A standalone narrative engine based on formal causality for generating branching stories with AI while maintaining verifiable coherence.**

---

## What is CNE?

A reusable framework that any project can integrate -- a game, a writing tool, an API, or a content generation pipeline.

**Coherence is a structural property of the engine, NOT of the LLM.**

```
┌──────────────────────────────────┐
│  AI proposes events              │
│         ↓                        │
│  Engine validates causal         │
│  coherence                       │
│         ↓                        │
│  Engine decides what happens     │
└──────────────────────────────────┘
```

---

## Current Status

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ **COMPLETED** | In-memory Core Engine (no dependencies) |
| **Phase 2** | ✅ **COMPLETED** | PostgreSQL persistence + async SQLAlchemy |
| **Phase 3** | ✅ **COMPLETED** | AI Adapter (Anthropic + Ollama + Mock) |
| **Phase 4** | ✅ **COMPLETED** | FastAPI REST API |
| **Phase 5** | 🔲 Pending | Public release on PyPI |

---

## Quickstart -- Core Engine Only (no dependencies)

```bash
# Install only the core (zero external dependencies)
pip install -e .

# Verify
python -c "import cne_core; print(cne_core.__version__)"

# Run core tests
python tests/test_fase1.py

# Run minimal example
python docs/examples/minimal_example.py
```

## Quickstart -- With PostgreSQL + REST API

```bash
# 1. Install all dependencies
pip install -e ".[all]"

# 2. Start PostgreSQL
docker-compose up -d

# 3. Create tables
alembic upgrade head

# 4. Run example
python examples/fase2_example.py

# 5. Start REST API
uvicorn api.main:app --reload

# 6. Run tests
pytest tests/ -v
```

---

## Core Concepts

### 1. Formal Model

```
CNE = (W, E, S, D, T, C, Φ)
```

- **W** = WorldDefinition (immutable seed)
- **E** = Narrative event space
- **S(t)** = World state at time t
- **D(t)** = Dramatic Vector with 7 meters
- **T** = Transition function (AI proposes -> engine validates)
- **C** = Causal graph (acyclic DAG)
- **Φ** = Dramatic evaluator (thresholds -> forced events)

**4 Guarantees:**
- ✅ **Causality**: The graph is always a valid DAG
- ✅ **Determinism**: State is reconstructible from snapshots
- ✅ **Versioning**: Git-like, you can go back on decisions
- ✅ **Consistency**: Dead entities do not act, variables stay in range

### 2. Dramatic Multi-Meter System (SDMM)

7 independent meters instead of a single indicator:

| Meter | What it measures |
|-------|------------------|
| `tension` | Active conflict level |
| `hope` | Perception that things can improve |
| `chaos` | World entropy |
| `rhythm` | Narrative pacing |
| `saturation` | Current arc exhaustion |
| `connection` | Emotional bond with characters |
| `mystery` | Unresolved questions |

**Thresholds -> Forced Events:**
```
tension > 85             ->  forced CLIMAX
hope < 10                ->  forced TRAGEDY
saturation > 95          ->  forced ARC CLOSURE
mystery + tension > 130  ->  CLIMATIC REVELATION
```

### 3. Standalone Architecture

```
┌────────────────────────────────┐
│  Any external client           │
│  (game, web, CLI...)           │
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

## Installation

### Core Engine Only (no external dependencies)

```bash
pip install -e .
```

**Python 3.11+ stdlib only** -- tests without PostgreSQL, API keys, or Docker.

### With PostgreSQL

```bash
pip install -e ".[persistence,dev]"
docker-compose up -d
alembic upgrade head
```

### With Local AI (Ollama -- free, no API key)

```bash
pip install -e ".[ai,persistence,dev]"

# Install Ollama: https://ollama.com
# Download model (3GB):
ollama pull gemma3:4b
```

### With Cloud AI (Anthropic)

```bash
pip install -e ".[ai,persistence,dev]"
export ANTHROPIC_API_KEY="sk-..."
```

### Everything Together

```bash
pip install -e ".[all]"
```

---

## Programmatic Usage

### Basic Example (In-Memory Core Engine)

```python
from cne_core import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core import StateMachine, NarrativeChoice, DramaticDelta

# 1. Create world
hero = Entity(
    name="Aldric",
    entity_type=EntityType.CHARACTER,
    attributes={"health": 100, "courage": 80}
)

world = WorldDefinition(
    name="The Shadow Realm",
    context="A medieval kingdom where dark magic threatens...",
    protagonist="Aldric, an exiled knight",
    era="Medieval fantasy",
    tone=NarrativeTone.DARK,
    initial_entities=[hero]
)

# 2. Start engine
engine = StateMachine(world)

# 3. Begin story
result = engine.start(
    initial_narrative="The kingdom is in danger...",
    initial_choices=[
        NarrativeChoice(text="Go to the palace"),
        NarrativeChoice(text="Flee to the mountains"),
    ]
)

# 4. Advance story
result = engine.advance_story(
    choice_text="Go to the palace",
    narrative_text="Aldric rides toward the capital...",
    summary="Aldric accepts the mission.",
    choices=[NarrativeChoice(text="Enter through the main gate")],
    dramatic_delta=DramaticDelta(tension=10, hope=-5)
)

print(result.display())
```

### With PostgreSQL

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

## REST API

Start the server:
```bash
uvicorn api.main:app --reload --port 8000
```

### Main Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/worlds` | Create WorldDefinition |
| `GET` | `/worlds/{world_id}` | Get world |
| `POST` | `/worlds/{world_id}/start` | Start story |
| `POST` | `/commits/{commit_id}/advance` | Make a decision |
| `GET` | `/commits/{commit_id}` | Commit state |
| `GET` | `/commits/{commit_id}/dramatic` | Dramatic vector |
| `GET` | `/health` | Server status |

Interactive documentation at `http://localhost:8000/docs` (Swagger UI).

---

## Integration

To connect your own persistence system or your own LLM to the engine, see the **[Integration Guide](docs/integration_guide.md)**.

It covers:
- How to implement `NarrativeRepository` (your database)
- How to implement `AIAdapter` (your LLM)
- Direct usage of the Python SDK
- Usage via REST API

---

## Tests

```bash
# In-memory Core Engine (no dependencies)
python tests/test_fase1.py

# Adapters + engine integration (no API key)
pytest tests/test_adapters.py -v

# REST API (requires Docker + PostgreSQL)
pytest tests/test_api.py -v

# Persistence (requires Docker + PostgreSQL)
pytest tests/test_persistence_integration.py -v

# All tests
pytest tests/ -v
```

---

## Project Structure

```
cne_core/                          # Core Engine
├── models/                        # Dataclasses (WorldDefinition, NarrativeEvent, EntityCreation, etc.)
├── engine/                        # CausalValidator, DramaticEngine, StateMachine
├── interfaces/                    # Abstract contracts (NarrativeRepository, AIAdapter)
└── ai/                            # ContextBuilder, ResponseValidator, ResponseSchema

adapters/                          # AIAdapter implementations
├── mock_adapter.py                # Mock for tests (deterministic)
├── anthropic_adapter.py           # Anthropic Claude
└── ollama_adapter.py              # Ollama (free local LLMs)

persistence/                       # PostgreSQL persistence
├── database.py                    # SQLAlchemy 2.0 async config
├── models/                        # ORM models (WorldORM, EventORM, CommitORM, EntityCreationORM)
├── repositories/                  # PostgreSQLRepository
└── queries/                       # Recursive CTEs (causal validation in SQL)

api/                               # FastAPI REST API
├── routers/                       # Endpoints (worlds, narrative, health)
├── services/                      # NarrativeServiceV2
├── models/                        # Request/Response schemas (Pydantic)
└── dependencies.py                # Dependency injection

cli/                               # Interactive CLI
migrations/                        # Alembic (4 migrations)
tests/                             # Tests (test_fase1, test_adapters, test_api, test_persistence_integration)
docs/                              # Documentation
web/                               # Web interface (in development)
```

---

## Roadmap

### ✅ Phase 1 -- Core Engine
- [x] Domain dataclasses
- [x] CausalValidator (acyclic DAG)
- [x] DramaticEngine (SDMM)
- [x] StateMachine (in-memory orchestrator)
- [x] Complete tests

### ✅ Phase 2 -- Persistence
- [x] Abstract interfaces (Repository pattern)
- [x] ORM models (SQLAlchemy 2.0 async)
- [x] PostgreSQLRepository
- [x] Recursive CTEs (causal validation in SQL)
- [x] Migrations (Alembic)
- [x] Docker Compose

### ✅ Phase 3 -- AI Adapter
- [x] AnthropicAdapter (Claude)
- [x] OllamaAdapter (free local LLMs)
- [x] MockAIAdapter (tests without API key)
- [x] ContextBuilder (active trunk)
- [x] ResponseValidator (JSON validation)

### ✅ Phase 4 -- REST API
- [x] FastAPI endpoints
- [x] NarrativeServiceV2 with persistence
- [x] Choices persisted in DB
- [x] Engine reconstruction from DB
- [x] Dynamic entity creation (characters, items, artifacts at runtime)
- [x] Dockerfile + Docker Compose with Ollama

### 🔲 Phase 5 -- Release
- [ ] PyPI release (`pip install cne-core`)
- [ ] Public Docker image
- [ ] Complete documentation

### 🔲 Phase 6 -- Academic Paper
- [ ] Initial draft
- [ ] Experiments and formal metrics
- [ ] Submit to AIIDE / IEEE CoG

---

## License

MIT -- See [LICENSE](LICENSE) for details.

---

## Contact

- **Repository**: [github.com/Squisix/causal_narrative_engine](https://github.com/Squisix/causal_narrative_engine)
- **Issues**: [Report a problem](https://github.com/Squisix/causal_narrative_engine/issues)
- **Author**: Marco Guerrero (mvsquisix@gmail.com)
