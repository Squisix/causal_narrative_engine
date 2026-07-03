# Integration Guide — Causal Narrative Engine (CNE)

This guide details how to integrate and build on top of the CNE framework.

There are two primary integration patterns:
1. **Python SDK**: Import the `cne_core` package directly into your local Python application.
2. **REST API**: Interact with CNE through HTTP endpoints from any technology stack.

---

## Core Architecture Overview

```
+-------------------------------------------------------------+
|                     External Game/App UI                    |
+------------------------------+------------------------------+
                               | SDK / HTTP REST
+------------------------------v------------------------------+
|                     StateMachine (Memory)                    |
|  Tracks state tree, active commits, world rules, and history|
+------------------------------+------------------------------+
                               |
       +-----------------------+-----------------------+
       |                                               |
+------v---------------+                       +-------v------+
| CausalValidator (DAG)|                       |DramaticEngine|
| Enforces acyclic     |                       | Evaluates Phi|
| logical pathways.    |                       | for pacing   |
+----------------------+                       +--------------+
```

---

## Pattern 1: Python SDK Usage

Import components directly and spin up an in-memory orchestrator:

```python
from cne_core.engine.state_machine import StateMachine
from cne_core.models.world import WorldDefinition, NarrativeTone

# Initialize world definition seed
world = WorldDefinition(
    name="Dungeon Explorer",
    context="A forgotten crypt holding ancient relics and monsters...",
    protagonist="Darius the rogue",
    era="Age of Ruin",
    tone=NarrativeTone.MYSTERIOUS,
    output_language="en"
)

# Spin up StateMachine
engine = StateMachine(world)

# Reconstruct state or start a new narrative path
# ...
```

---

## Pattern 2: REST API Usage

Clients connect directly to the FastAPI server. See `docs/api_guide.md` for a complete breakdown of endpoints, payloads, and returned structures.

---

## Extensible Interfaces (ABCs)

CNE defines strict abstract classes (`ABC`) to decouple infrastructure from domain logic.

### 1. Persistent Storage (`NarrativeRepository`)
Connect your choice of database (PostgreSQL, DynamoDB, MongoDB, SQLite) by implementing:
- `save_world()`
- `get_world()`
- `save_commit()`
- `get_commit()`

### 2. AI Backends (`AIAdapter`)
Support additional AI platforms (OpenAI, Anthropic, Ollama, local models) by implementing:
- `generate_narrative(context: NarrativeContext) -> NarrativeProposal`
