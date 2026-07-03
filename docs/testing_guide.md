# CNE Testing Guide

CNE features a rigorous test suite designed to verify domain properties, persistence mapping, REST endpoints, and mock AI generations.

---

## Testing Framework
We use **pytest** as our test runner and test assertion suite.

---

## Test Organization

| Test File | Required Environment | Description |
|-----------|-----------------------|-------------|
| `tests/test_fase1.py` | None (Fast) | Core validation: cycle checks, dramatic meters, climax pacing |
| `tests/test_adapters.py` | None (Fast) | Mock AI generation, response validation, entity creations |
| `tests/test_persistence_integration.py` | Docker PostgreSQL | Database mappings, recursive CTE queries |
| `tests/test_api.py` | Docker PostgreSQL | Full API controller endpoint and status validation |

---

## Commands

### 1. Rapid Core Tests (No dependencies)
Runs pure domain unit tests instantaneously.
```bash
python -m pytest tests/test_fase1.py tests/test_adapters.py -v
```

### 2. Integration Tests (Requires database)
Before running, spin up Docker and run database schema migrations.
```bash
docker-compose up -d
alembic upgrade head
python -m pytest tests/ -v
```

### 3. Coverage Analysis
To check coverage and write HTML reports:
```bash
python -m pytest --cov=cne_core --cov=adapters --cov-report=html -v
```
The result is written to `htmlcov/index.html`.
