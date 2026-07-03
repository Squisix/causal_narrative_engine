---
name: run-tests
description: How to run CNE project tests
trigger: When the user requests running tests, verifying work, or before committing
---

# Running Tests — Causal Narrative Engine

## Available Tests

| File | Requires | What It Tests |
|------|----------|---------------|
| `tests/test_fase1.py` | Nothing | Core Engine: DAG, SDMM, StateMachine, P1-P4 |
| `tests/test_adapters.py` | Nothing | MockAdapter, engine integration, entity creation, 5-tuple |
| `tests/test_api.py` | Docker + PostgreSQL | Full REST API (17 tests) |
| `tests/test_persistence_integration.py` | Docker + PostgreSQL | PostgreSQLRepository integration |
| `tests/test_anthropic_adapter.py` | ANTHROPIC_API_KEY | Real generation with Claude (consumes credits) |

## Commands

### Fast (No External Dependencies)

```bash
python -m pytest tests/test_fase1.py tests/test_adapters.py -v
```

### With Docker (API + Persistence)

```bash
docker-compose up -d
alembic upgrade head
python -m pytest tests/ -v
```

### Without Anthropic API Key

```bash
python -m pytest -m "not anthropic_api" -v
```

### Code Coverage

```bash
python -m pytest --cov=cne_core --cov=adapters --cov-report=html -v
```

## Important Notes

- `conftest.py` contains shared fixtures for PostgreSQL database sessions.
- API tests utilize `httpx.AsyncClient` with `ASGITransport`.
- **CRITICAL**: By default, `/advance` requests use `"adapter_type": "mock"`. If you want to use external local models during testing, pass `"adapter_type": "ollama"` explicitly.
- Anthropic integration tests are skipped automatically if the API key is not configured in the environment.
