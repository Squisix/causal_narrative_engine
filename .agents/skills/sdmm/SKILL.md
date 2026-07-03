---
name: sdmm
description: Dramatic Multi-Meter System — the 7 meters, interactions, and thresholds
trigger: When working with DramaticEngine, dramatic vectors, forced events, or thresholds
---

# Dramatic Multi-Meter System (DMMS / SDMM)

The core innovation of the project. Replaces "tree health" with a formal 7-dimensional state vector.

## The 7 Meters

| Meter | Range | Start | What It Measures |
|-------|-------|-------|------------------|
| `tension` | [0-100] | 30 | Level of active conflict |
| `hope` | [0-100] | 60 | Perception that things can improve |
| `chaos` | [0-100] | 20 | World entropy and unpredictable events |
| `rhythm` | [0-100] | 50 | Narrative pacing and speed |
| `saturation` | [0-100] | 0 | Exhaustion level of the current story arc |
| `connection` | [0-100] | 40 | Emotional depth and bonding with characters |
| `mystery` | [0-100] | 50 | Unresolved questions and secrets |

## Automatic Interactions (Applied after every delta)

```
tension > 50     ->  hope -= ((tension - 50) // 10) * 2
chaos > 60       ->  rhythm += (chaos - 60) // 10
saturation > 70  ->  connection -= (saturation - 70) // 5
hope < 20        ->  mystery += 3
```

All values are clamped to [0, 100] after applying these interactions.

## Thresholds -> Forced Events (Phi)

### Priority 1: Combinations
```
mystery > 65 AND tension > 65    ->  CLIMAX_REVELATION
connection > 70 AND tension > 60 ->  EMOTIONAL_MOMENT
```

### Priority 2: Individuals
```
saturation > 95                  ->  ARC_CLOSURE
tension > 85                     ->  CLIMAX
hope < 10                        ->  TRAGEDY
chaos > 80                       ->  CHAOS_STORM
saturation > 85                  ->  PLOT_TWIST
tension < 15                     ->  DISRUPTIVE
hope > 90                        ->  UNEXPECTED_THREAT
rhythm > 90 (x3 turns in a row)  ->  NARRATIVE_REST
```

## How a Forced Event Works

1. `DramaticEngine.evaluate_thresholds()` returns a `ForcedEventConstraint | None`.
2. If a constraint exists, it is appended to the `NarrativeContext` for the AI.
3. The AI receives a **mandatory constraint instruction** in the system prompt.
4. The forced event is integrated causally into the DAG — it is not an arbitrary external interruption, but a formal consequence of the events that elevated the meters.

## Key Files

- `cne_core/engine/dramatic_engine.py` — `DramaticEngine`, `DramaticVector`, `ForcedEventConstraint`, `ForcedEventType`
- `cne_core/models/event.py` — `DramaticDelta` (the deltas applied by each event)
- `cne_core/ai/context_builder.py` — Formatting the dramatic state for the AI prompt

## DramaticDelta

```python
@dataclass
class DramaticDelta:
    tension: int = 0
    hope: int = 0
    chaos: int = 0
    rhythm: int = 0
    saturation: int = 0
    connection: int = 0
    mystery: int = 0
```

Each narrative event can include a `DramaticDelta` that mutates the vector. The engine automatically processes the cross-meter interactions and clamps the results afterwards.
