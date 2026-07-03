# CNE Architecture Guide

The CNE architecture separates pure, deterministic narrative mechanics from asynchronous persistence, API controllers, and AI integrations.

## Architecture Diagram

```
+-------------------------------------------------------------+
|                        FastAPI API Layer                     |
|  Controllers validate request schemas and inject services.   |
+------------------------------+------------------------------+
                               | async session
+------------------------------v------------------------------+
|                     NarrativeServiceV2                       |
|   Coordinates DB transactions, state loading, and AI calls.  |
+--------------+-------------------------------+--------------+
               |                               |
+--------------v---------------+       +-------v--------------+
|       PostgreSQL DB          |       |     AI Adapter       |
|  Tracks tables: worlds,      |       |  Transforms contexts |
|  entities, events, commits.  |       |  to JSON proposals.  |
+--------------+---------------+       +-------+--------------+
               |                               |
+--------------v-------------------------------v--------------+
|                        StateMachine                         |
|   Synchronous, in-memory domain model orchestrating logic.  |
|   Enforces P1-P4 mathematical properties.                    |
+------------------------------+------------------------------+
                               |
       +-----------------------+-----------------------+
       |                                               |
+------v---------------+                       +-------v------+
|    CausalValidator   |                       |DramaticEngine|
|  BFS cycle checking  |                       |  Meters &    |
|  for event graph.    |                       |  Constraints |
+----------------------+                       +--------------+
```

## Guiding Principles

### 1. Separation of Domain (Core) and Infrastructure (Adapters)
`cne_core` is 100% synchronous and has NO dependencies on databases, HTTP clients, or framework libraries. This makes the core lightweight and portable (`pip install cne-core`). Asynchronous operations are isolated inside `persistence/` and `api/`.

### 2. State Reconstruction (P2 Determinism)
When jumps/goto are made, rather than mutating states on the fly, CNE completely wipes active entities (`self._entities.clear()`) and rebuilds the active narrative state by replaying sequential snapshots and deltas from root up to the target commit.

### 3. Structural Coherence is the Engine's Responsibility
The LLM acts as a creative proposal generator. CNE enforces the rules of the world, ensures dead entities cannot act, checks for causal cycle violations, and manages automatic dramatic meter updates.

## Dramatic Multi-Meter System (DMMS / SDMM)

The DramaticEngine tracks a 7-dimensional vector:
- **Tension**: Level of active conflict.
- **Hope**: Perception that things will improve.
- **Chaos**: Narrative entropy and unpredictability.
- **Rhythm**: Pacing speed.
- **Saturation**: Exhaustion of the current arc.
- **Connection**: Relationship with characters.
- **Mystery**: Level of unanswered questions.

It applies automatic interactions:
- High tension erodes hope.
- High chaos increases narrative rhythm.
- High saturation lowers character connection.
- Extremely low hope increases mystery.

If any meter crosses critical thresholds, the engine enforces a forced constraint (such as a CLIMAX, TRAGEDY, PLOT_TWIST, or CLIMAX_REVELATION) on the AI's next prompt.
