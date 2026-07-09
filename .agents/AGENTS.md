# Causal Narrative Engine (CNE) — Literary Tree

> Read this before modifying any source code.
> Available skills are in `.agents/skills/` for detailed reference.

---

## What is this Project

An **independent narrative engine** based on formal causality for generating branching stories with AI while maintaining verifiable coherence. The engine is a reusable framework that any project can integrate — a game, a writing tool, an API, or a content generation pipeline.

**The engine is the product.** Client integrations are the responsibility of the integrator.

Goals:
1. **Independent Engine**: `pip install cne-core` and it works. No coupling to clients.
2. **Extensible by Design**: abstract interfaces (ABCs) for persistence and AI.
3. **Academic Paper**: publish at AIIDE / IEEE CoG.

---

## Formal Model

```
CNE = (W, E, S, D, T, C, Phi)
```

| Symbol | Name | Description |
|--------|------|-------------|
| `W` | WorldDefinition | Immutable Seed: genre, tone, rules, constraints |
| `E` | Event Space | All possible narrative events |
| `S(t)` | Narrative State | `(Entities(t), EntityCreations(t), WorldVars(t), D(t), History(t))` |
| `D(t)` | Dramatic Vector | `(tension, hope, chaos, rhythm, saturation, connection, mystery) in [0,100]^7` |
| `T` | Transition Function | `S(t+1) = T(S(t), choice, AI_proposal)` |
| `C` | Causal Graph | Directed Acyclic Graph (DAG) of events. No cycles. |
| `Phi` | Dramatic Function | Evaluates D(t) thresholds -> ForcedEventConstraint | None |

**4 guaranteed properties:**
- **P1 Causality**: The event graph is always a DAG (Acyclic).
- **P2 Determinism**: `S(t)` is fully reconstructible from snapshots + deltas.
- **P3 Versioning**: Every choice = commit with parent_id (Git-like tree).
- **P4 Consistency**: Dead entities cannot act, variables remain in valid range.

---

## Architecture

```
+------------------------------------------------------+
|               Any External Client                    |
|   (game, API, CLI, writer tool, etc.)                |
+---------------------+--------------------------------+
                      | import cne_core  /  HTTP  /  SDK
+---------------------v--------------------------------+
|            FastAPI REST API  [COMPLETED]             |
|    api/ — NarrativeServiceV2 + routers               |
+---------------------+--------------------------------+
                      |
+---------------------v--------------------------------+
|           Core Engine  —  cne_core/                  |
|   CausalValidator  |  DramaticEngine  |  StateMachine|
|   ContextBuilder   |  ResponseSchema  |  Interfaces  |
+----------+------------------------------+-----------+
           |                              |
+----------v----------+      +-----------v------------+
|  Persistence Layer  |      |      AI Adapter        |
|                     |      |                        |
|  Interface ABC      |      |  Interface ABC         |
|  PostgreSQL [OK]    |      |  Anthropic [OK]        |
|  Redis Cache [OK]   |      |  Ollama [OK]           |
|                     |      |  Mock [OK]             |
+---------------------+      +------------------------+
```

**Key Principle**: Coherence is a structural property of the engine, NOT of the LLM.
The AI proposes. The engine validates and decides.

---

## Project Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1 | COMPLETED | Memory-only Core Engine (no external dependencies) |
| Phase 2 | COMPLETED | PostgreSQL persistence + async SQLAlchemy |
| Phase 3 | COMPLETED | AI Adapter (Anthropic + Ollama + Mock) |
| Phase 4 | COMPLETED | FastAPI REST API |
| Phase 5 | Pending | Public PyPI release |
| Phase 6 | Pending | Academic paper publication |

---

## Directory Structure

```
cne_core/                          # Core Engine
├── models/
│   ├── world.py                   # WorldDefinition, Entity, EntityType, NarrativeTone
│   ├── event.py                   # NarrativeEvent, CausalEdge, EntityDelta, EntityCreation,
│   │                              # WorldVariableDelta, DramaticDelta
│   └── commit.py                  # NarrativeCommit, Branch, NarrativeChoice
├── engine/
│   ├── causal_validator.py        # CausalValidator: DAG cycle detection (BFS)
│   ├── dramatic_engine.py         # DramaticEngine: Complete SDMM with Phi
│   └── state_machine.py           # StateMachine: in-memory state orchestrator
├── interfaces/
│   ├── repository.py              # NarrativeRepository ABC
│   └── ai_adapter.py              # AIAdapter ABC + NarrativeContext/NarrativeProposal
└── ai/
    ├── context_builder.py         # ContextBuilder: active context trunk builder for LLMs
    ├── response_schema.py         # NarrativeResponse (Pydantic) + to_core_models()
    └── response_validator.py      # JSON schema and rule validation for AI proposals

adapters/                          # AIAdapter Implementations
├── mock_adapter.py                # MockAdapter: deterministic for fast unit testing
├── anthropic_adapter.py           # AnthropicAdapter: Claude API integration
└── ollama_adapter.py              # OllamaAdapter: local open-source LLMs (gemma, llama)

persistence/                       # PostgreSQL Persistence & Caching
├── database.py                    # DatabaseConfig, async session factory
├── cache.py                       # CacheBackend (RedisCache, NullCache) for optimization
├── models/
│   ├── world_orm.py               # WorldORM, EntityORM
│   ├── event_orm.py               # EventORM, EntityDeltaORM, EntityCreationORM
│   └── commit_orm.py              # CommitORM, BranchORM, ChoiceORM, DramaticStateORM
├── repositories/
│   └── postgresql_repository.py   # PostgreSQLRepository implementation
└── queries/
    └── causal_queries.py          # CTE recursive query for causal path database verification

api/                               # FastAPI REST API
├── main.py                        # FastAPI startup with routers
├── config.py                      # Global environment settings
├── dependencies.py                # Dependency injection providers
├── routers/
│   ├── worlds.py                  # World CRUD endpoints
│   ├── narrative.py               # start, advance, goto, commits endpoints
│   └── health.py                  # Server health check
├── services/
│   └── narrative_service_v2.py    # Service orchestrator connecting Core and DB
└── models/
    ├── requests.py                # Pydantic request schemas
    └── responses.py               # Pydantic response schemas

cli/                               # CLI interactive player
migrations/                        # Alembic DB migrations
tests/                             # Automated test suites
web/                               # Web UI for playing and analyzing games
```

---

## AI JSON Contract

The AI must return the following JSON structure (validated by ResponseValidator):

```json
{
  "narrative": "Immersive narrative text of 150-250 words",
  "summary": "1-sentence causal summary of this chapter for the history trunk",
  "choices": ["option A", "option B", "option C"],
  "choice_tones": ["confrontational", "diplomatic", "evasive"],
  "entity_deltas": [{"entity_id": "uuid", "attribute": "health", "old_value": 100, "new_value": 85}],
  "entity_creations": [
    {"entity_name": "Name", "entity_type": "character|artifact|faction|location",
     "attributes": {"health": 100, "possessed_by": null, "location": "place", "usable": true, "effect": "description"}}
  ],
  "world_deltas": [{"variable": "political_stability", "old_value": 60, "new_value": 48}],
  "dramatic_deltas": {
    "tension": 15, "hope": -8, "chaos": 5,
    "rhythm": 0, "saturation": 8, "connection": -3, "mystery": 10
  },
  "causal_reason": "Why this event occurs given the current state",
  "forced_event_type": null,
  "is_ending": false
}
```

`to_core_models()` returns a **5-tuple**:
```python
entity_deltas, entity_creations, world_deltas, dramatic_delta, choices = response.to_core_models()
```

---

## REST API Endpoints

```
POST   /worlds                       # Create WorldDefinition
GET    /worlds/{world_id}            # Retrieve world metadata
DELETE /worlds/{world_id}            # Delete world and all branches
POST   /worlds/{world_id}/start      # Start story on a world seed
GET    /worlds/{world_id}/commits    # List commits for world
POST   /commits/{commit_id}/advance  # Advance story with a decision
GET    /commits/{commit_id}          # Retrieve state of a commit
GET    /commits/{commit_id}/dramatic # Get dramatic vector details
POST   /commits/{commit_id}/goto     # Jump/rewind to a previous commit
GET    /health                       # Get server health status
```

---

## Coding Conventions

### Naming
- **Classes**: PascalCase (`NarrativeCommit`, `DramaticEngine`)
- **Methods/variables**: snake_case (`advance_story`, `current_commit_id`)
- **Constants/enums**: UPPER_SNAKE or PascalCase for Enums
- **IDs**: always `str` (serializable UUIDs)

### Patterns
- **Dataclasses** for domain models (`@dataclass`)
- **`str` + `Enum`** for enums to ensure direct JSON serializability
- **`field(default_factory=...)`** for mutable dataclass defaults
- **`ABC`** for abstract interfaces (Repository, AIAdapter) — keep core free from database logic
- **Async** in persistence/api layers — the Core Engine remains completely synchronous

### Custom Exceptions
```python
class CausalCycleError(Exception): ...
class EventNotFoundError(Exception): ...
class ValidationError(Exception): ...
```

---

## Included Implementations

| Component | Implementation | When to Use |
|-----------|----------------|-------------|
| Repository | `PostgreSQLRepository` | Production and integration tests |
| Cache | `RedisCache` | Redis-backed caching for trunks, worlds, and choices in production |
| Cache | `NullCache` | No-op caching fallback when Redis is unconfigured |
| AIAdapter | `MockAdapter` | Fast, deterministic mock AI for testing without API keys |
| AIAdapter | `AnthropicAdapter` | Production deployment using Claude models |
| AIAdapter | `OllamaAdapter` | Local open-source LLMs (gemma, llama) |

---

## Useful Commands

```bash
# Core Engine memory tests
python -m pytest tests/test_fase1.py tests/test_adapters.py -v

# Full suite (requires Docker + PostgreSQL)
docker-compose up -d
alembic upgrade head
pytest tests/ -v

# Run FastAPI Server
uvicorn api.main:app --reload --port 8000
```

---

## Critical Design Mandates

- **Do not use `vitality`** — replaced entirely by `DramaticVector`.
- **`StateMachine` is synchronous** — async mechanics belong exclusively in `NarrativeServiceV2`.
- **The Core Engine never imports from `persistence/`** — dependencies always flow inwards.
- **The AI never mutates state directly** — it proposes deltas, and the engine validates and applies them.
- **`go_to_commit()` restores from snapshots** — clears `self._entities` and rebuilds the state.
- **Entity creations run BEFORE entity deltas** — allowing deltas to reference newly introduced entities.
- **`to_core_models()` returns a 5-tuple** — all adapters unpack exactly 5 variables.
- **`AdvanceNarrativeRequest` defaults to `adapter_type="mock"`** — safe and fast by default.
- **Do not couple the Core Engine to specific clients** — importing FastAPI or Flutter in core is a structural error.
- **Redis Cache is optional** — if `REDIS_URL` is unconfigured, `NullCache` is used and the app functions normally.
