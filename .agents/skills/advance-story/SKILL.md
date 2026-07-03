---
name: advance-story
description: How the advance story flow and the entity creation system work
trigger: When working with StateMachine.advance_story, entity creation, or the 5-tuple from to_core_models
---

# Flow of advance_story and Entity Creation

## Execution Order in StateMachine.advance_story()

1. **_apply_entity_creations()** — Creates new entities (characters, artifacts, locations)
2. **_apply_entity_deltas()** — Modifies attributes of existing entities
3. **_apply_world_deltas()** — Modifies global variables of the world
4. **DramaticEngine.apply_delta()** — Updates the 7-dimensional dramatic vector
5. **DramaticEngine.evaluate_thresholds()** — Evaluates if any threshold is crossed (-> forced event)
6. **Create NarrativeEvent** — With all deltas, creations, and causal_reason
7. **CausalValidator.add_edge()** — Validates that the DAG contains no cycles
8. **Create NarrativeCommit** — With full-state snapshots

**CRITICAL**: Entity creation runs BEFORE entity deltas so that deltas can reference newly created entities in the same turn.

## EntityCreation Dataclass

```python
@dataclass
class EntityCreation:
    entity_name: str
    entity_type: str  # "character", "faction", "artifact", "location"
    attributes: dict[str, Any] = field(default_factory=dict)
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))
```

File: `cne_core/models/event.py`

## Special Attributes for Artifacts/Items

```python
{
    "possessed_by": null,    # who holds it (null = available in the environment)
    "location": "altar",     # where it is located
    "usable": true,          # whether it can be used right now
    "effect": "Opens doors"  # what effect or utility it has
}
```

## 5-Tuple of to_core_models()

`NarrativeResponse.to_core_models()` returns exactly 5 values:

```python
entity_deltas, entity_creations, world_deltas, dramatic_delta, choices = response.to_core_models()
```

All AI adapters (mock, anthropic, ollama) unpack these 5 values in `_convert_to_proposal`.

## go_to_commit and Dynamic Entities

When jumping to a previous commit with `go_to_commit()`:
- Executing `self._entities.clear()` — clears ALL active entities
- Reconstructs the state entirely from the snapshot of the target commit
- Entities created after that commit will NOT appear
- Uses the `created_at_depth` field in the snapshot to reconstruct with the `Entity()` constructor

## Persistence of Entity Creation

In `NarrativeServiceV2._persist_result()`:
1. The event is saved with `repo.save_event()` (includes EntityCreationORM records)
2. An `Entity` object is created and persisted with `repo.save_entity(entity, world_id)`

Audit table: `entity_creations` (migration 004)
