# Testing Guide - Causal Narrative Engine

This document explains how to run the different types of tests and which ones require API keys.

---

## Quick Summary

| Test Suite | Requires API Key | Requires Docker | Command |
|------------|------------------|-----------------|---------|
| **Core Engine** (test_fase1) | ❌ No | ❌ No | `pytest tests/test_fase1.py -v` |
| **Adapters** (test_adapters) | ❌ No | ❌ No | `pytest tests/test_adapters.py -v` |
| **REST API** (test_api) | ❌ No | ✅ Yes | `pytest tests/test_api.py -v` |
| **Persistence** (test_persistence) | ❌ No | ✅ Yes | `pytest tests/test_persistence_integration.py -v` |
| **AnthropicAdapter** | ✅ Yes | ❌ No | `pytest tests/test_anthropic_adapter.py -v` |

---

## Tests WITHOUT API Key or Docker (Free, Fast)

### ✅ Core Engine (test_fase1.py)

```bash
pytest tests/test_fase1.py -v
```

**What it tests:**
- CausalValidator (DAG cycle detection)
- DramaticEngine (thresholds, forced events, SDMM)
- StateMachine (commits, branches, versioning)
- Properties P1-P4 (Causality, Determinism, Versioning, Consistency)

### ✅ Adapters (test_adapters.py)

```bash
pytest tests/test_adapters.py -v
```

**What it tests:**
- MockAdapter: deterministic generation, player decisions, forced events, statistics, error mode
- MockAdapter + StateMachine integration: full generate -> process -> state flow
- Dynamic entity creation: creating characters and artifacts at runtime
- Entity creation + go_to_commit: entities created later do not appear when navigating back
- ResponseSchema: parsing entity_creations and the 5-tuple from to_core_models()

---

## Tests WITH Docker (Require PostgreSQL)

These tests require PostgreSQL running:

```bash
docker-compose up -d
alembic upgrade head
```

### ✅ REST API (test_api.py)

```bash
pytest tests/test_api.py -v
```

**What it tests:**
- World CRUD (create, get, delete)
- Full narrative flow (start -> advance -> advance)
- Commit navigation (goto, list, existing_paths)
- Dramatic state per commit
- Causal reason in responses
- Custom player choices

### ✅ Persistence (test_persistence_integration.py)

```bash
pytest tests/test_persistence_integration.py -v
```

**What it tests:**
- PostgreSQLRepository: save/get for worlds, commits, events
- Entity persistence and entity creation records
- Dramatic state snapshots and deltas

---

## Tests WITH API Key (Cost Money)

### ⚠️ Required Configuration

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` and add your API key:**
   ```bash
   ANTHROPIC_API_KEY=sk-ant-api03-your-real-key-here
   ```

3. **Get your API key at:**
   https://console.anthropic.com/settings/keys

### ✅ AnthropicAdapter (test_anthropic_adapter.py)

```bash
pytest tests/test_anthropic_adapter.py -v
```

**What it tests:**
- Real generation with Claude
- Response to player decisions
- AI response validation
- Statistics tracking (tokens, calls, etc.)

**Estimated cost:** ~$0.01 USD per full run

Tests marked with `@pytest.mark.anthropic_api` are **automatically skipped** if you don't have `ANTHROPIC_API_KEY` configured.

---

## Tests with Ollama (Free, requires Ollama installed)

OllamaAdapter is tested manually since it requires a local LLM running.

### Requirements

```bash
# 1. Install Ollama: https://ollama.com
# 2. Download model
ollama pull gemma3:4b

# 3. Verify Ollama is running
curl http://localhost:11434/api/tags
```

### Test via REST API

```bash
# 1. Start server
uvicorn api.main:app --reload

# 2. Create world
curl -X POST http://localhost:8000/worlds \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "context": "Fantasy", "protagonist": "Hero", "era": "Medieval", "tone": "dark"}'

# 3. Start narrative with Ollama
curl -X POST http://localhost:8000/worlds/{world_id}/start \
  -H "Content-Type: application/json" \
  -d '{"adapter_type": "ollama"}'
```

### Recommended Models

| Model | RAM | Notes |
|-------|-----|-------|
| `gemma3:4b` (default) | ~3GB | Good quality/speed balance |
| `qwen3:4b` | ~3GB | Very good at following JSON instructions |
| `llama3.2:3b` | ~2GB | Intermediate, lighter |
| `mistral:7b` | ~4GB | Better quality, requires more RAM |

---

## Recommended Strategy

### During development (day-to-day)

```bash
# Fast, free, no Docker
pytest tests/test_fase1.py tests/test_adapters.py -v
```

### Before committing

```bash
# All tests without API + coverage
pytest --cov=cne_core --cov=adapters -v
```

### Before release

```bash
# Everything including real API
pytest -v
```

### In CI/CD (GitHub Actions, etc.)

```bash
# Only tests without API (to avoid costs)
pytest -m "not anthropic_api" -v --cov=cne_core --cov=adapters
```

---

## Test Structure

```
tests/
├── conftest.py                    # Shared fixtures (PostgreSQL session, etc.)
├── test_fase1.py                  # In-memory Core Engine (free, no dependencies)
├── test_adapters.py               # MockAdapter + engine integration + entity creation
├── test_api.py                    # Full REST API (requires Docker)
├── test_persistence_integration.py # PostgreSQL repository (requires Docker)
└── test_anthropic_adapter.py      # Real Anthropic API (costs money, skipped without key)
```

---

## Useful Commands

```bash
# Single test
pytest tests/test_adapters.py::test_basic_generation -v

# Single file
pytest tests/test_api.py -v

# With coverage
pytest --cov=cne_core --cov=adapters --cov-report=html -v

# Exclude API tests
pytest -m "not anthropic_api" -v

# Run in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto -v
```

---

## Troubleshooting

### ❌ "ImportError: cannot import name 'AsyncAnthropic'"

```bash
pip install anthropic
```

### ❌ "ANTHROPIC_API_KEY is not configured"

1. Verify that `.env` exists
2. Verify that it contains `ANTHROPIC_API_KEY=sk-ant-...`
3. Verify that the key is not the example value

### ❌ API tests fail with timeout

API tests use MockAdapter by default. If they fail with timeout, verify that PostgreSQL is running:
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

**Q: Can I develop without an API key?**
A: Yes. Use MockAdapter for everything. It is deterministic and free.

**Q: Can I test with AI for free?**
A: Yes. Install [Ollama](https://ollama.com), download `gemma3:4b`, and use `adapter_type: "ollama"`.

**Q: Do Anthropic tests run automatically?**
A: No. They are skipped if no API key is configured.

**Q: What Anthropic model does it use by default?**
A: Configurable via `ANTHROPIC_MODEL` in `.env`.

**Q: Can I use a different Ollama model?**
A: Yes. Edit `OLLAMA_MODEL` in `.env` or pass `model=` to the constructor.
