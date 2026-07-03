"""
cne_core/models — Domain dataclasses

All models are immutable dataclasses (except for internal attributes).
They use str for IDs (serializable UUIDs) and Enum for types.
"""

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.models.event import (
    NarrativeEvent,
    EventType,
    CausalEdge,
    CausalRelationType,
    EntityDelta,
    WorldVariableDelta,
    DramaticDelta,
)
from cne_core.models.commit import NarrativeCommit, Branch, NarrativeChoice

__all__ = [
    "WorldDefinition",
    "Entity",
    "EntityType",
    "NarrativeTone",
    "NarrativeEvent",
    "EventType",
    "CausalEdge",
    "CausalRelationType",
    "EntityDelta",
    "WorldVariableDelta",
    "DramaticDelta",
    "NarrativeCommit",
    "Branch",
    "NarrativeChoice",
]
