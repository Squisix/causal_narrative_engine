"""
persistence/models — ORM models (SQLAlchemy)

Mapean los dataclasses del core a tablas SQL.

Convención de nombres:
- Dataclass: WorldDefinition, NarrativeEvent, etc.
- ORM model: WorldORM, EventORM, etc.
- Tabla SQL: worlds, events, etc. (snake_case plural)
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
]
