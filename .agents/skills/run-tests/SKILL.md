---
name: run-tests
description: Como ejecutar los tests del proyecto CNE
trigger: Cuando el usuario pida correr tests, verificar que algo funciona, o antes de commit
---

# Ejecutar Tests — Causal Narrative Engine

## Tests disponibles

| Archivo | Requiere | Que testea |
|---------|----------|------------|
| `tests/test_fase1.py` | Nada | Core Engine: DAG, SDMM, StateMachine, P1-P4 |
| `tests/test_adapters.py` | Nada | MockAdapter, integracion engine, entity creation, 5-tuple |
| `tests/test_api.py` | Docker + PostgreSQL | API REST completa (17 tests) |
| `tests/test_persistence_integration.py` | Docker + PostgreSQL | PostgreSQLRepository |
| `tests/test_anthropic_adapter.py` | ANTHROPIC_API_KEY | Generacion real con Claude (cuesta dinero) |

## Comandos

### Rapido (sin dependencias externas)

```bash
pytest tests/test_fase1.py tests/test_adapters.py -v
```

### Con Docker (API + persistencia)

```bash
docker-compose up -d
alembic upgrade head
pytest tests/ -v
```

### Sin API key de Anthropic

```bash
pytest -m "not anthropic_api" -v
```

### Coverage

```bash
pytest --cov=cne_core --cov=adapters --cov-report=html -v
```

## Notas importantes

- `conftest.py` tiene fixtures compartidos para PostgreSQL sessions
- Los tests de API usan `httpx.AsyncClient` con `ASGITransport`
- **CRITICO**: Todos los POST a `/advance` deben incluir `"adapter_type": "mock"` en el body JSON. Si no se pasa, defaultea a `"ollama"` y los tests fallan por timeout intentando conectar a Ollama local.
- Los tests de Anthropic se skipean automaticamente si no hay API key configurada
