"""
persistence/models — ORM models (SQLAlchemy)

Map the core dataclasses to SQL tables.

Naming convention:
- Dataclass: WorldDefinition, NarrativeEvent, etc.
- ORM model: WorldORM, EventORM, etc.
- SQL table: worlds, events, etc. (snake_case plural)
"""

from persistence.models.world_orm import WorldORM, EntityORM
from persistence.models.event_orm import (
    EventORM,
    CausalEdgeORM,
    EntityDeltaORM,
    WorldVariableDeltaORM,
)
from persistence.models.commit_orm import (
    CommitORM,
    BranchORM,
    DramaticStateORM,
    DramaticDeltaORM,
    ChoiceORM,
)

__all__ = [
    "WorldORM",
    "EntityORM",
    "EventORM",
    "CausalEdgeORM",
    "EntityDeltaORM",
    "WorldVariableDeltaORM",
    "CommitORM",
    "BranchORM",
    "DramaticStateORM",
    "DramaticDeltaORM",
    "ChoiceORM",
]
