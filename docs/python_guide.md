# CNE Python Style and Code Guide

This guide describes Python coding conventions and language features utilized across CNE codebase.

---

## Coding Style Rules
- We strictly adhere to **PEP 8** specifications.
- **Naming Conventions**:
  - Class names: PascalCase (e.g. `CausalValidator`, `StateMachine`).
  - Function and variable names: snake_case (e.g. `save_world`, `current_commit_id`).
  - Constants and Enums: UPPER_SNAKE (e.g. `ForcedEventType.CLIMAX_REVELATION`).
  - IDs and UUIDs are kept as `str` to avoid JSON serialization complications.

---

## Domain Modeling with Dataclasses

Dataclasses (`@dataclass`) are used extensively for clean, lightweight in-memory domain structures in `cne_core/models/`:

```python
from dataclasses import dataclass, field
from typing import Any
import uuid

@dataclass
class Entity:
    name: str
    entity_type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
```
*Note*: Never use mutable empty objects like `[]` or `{}` directly as class default properties. Always use `field(default_factory=...)` to avoid shared reference bugs between multiple instances.

---

## Abstract Base Classes (ABCs)

To ensure extensible decouplings, dependencies flow inwards towards abstract contracts rather than outwards towards databases or network connectors:

```python
from abc import ABC, abstractmethod
from cne_core.models.world import WorldDefinition

class NarrativeRepository(ABC):
    @abstractmethod
    async def save_world(self, world: WorldDefinition) -> None:
        pass
```
Any database plugin (PostgreSQL, SQLite, DynamoDB) can implement this interface without modifying core code.

---

## Type Annotations & Safety
- **Type Hints** are mandatory for all public functions and class variables.
- We avoid arbitrary `cast` or type bypass mechanisms. Type safety is strictly preserved.
