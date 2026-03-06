"""
cne_core/models — Dataclasses del dominio

Todos los modelos son dataclasses inmutables (excepto los atributos internos).
Usan str para IDs (UUIDs serializables) y Enum para tipos.
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
