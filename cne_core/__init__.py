"""
cne_core — Causal Narrative Engine Core

El motor narrativo independiente. Puede usarse sin dependencias externas
(Fase 1 en memoria) o con PostgreSQL (Fase 2).

Exports principales:
- WorldDefinition, Entity, NarrativeTone
- NarrativeEvent, EventType, DramaticDelta
- NarrativeCommit, Branch
- CausalValidator, DramaticEngine, StateMachine

Interfaces:
- NarrativeRepository (para persistencia)
- AIAdapter (para generación narrativa)
"""

__version__ = "0.2.0"  # Fase 2

# Models
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

# Engine components
from cne_core.engine.causal_validator import CausalValidator, CausalCycleError
from cne_core.engine.dramatic_engine import (
    DramaticEngine,
    DramaticVector,
    ForcedEventType,
    ForcedEventConstraint,
)
from cne_core.engine.state_machine import StateMachine, StoryAdvanceResult

# Interfaces
from cne_core.interfaces.repository import NarrativeRepository
from cne_core.interfaces.ai_adapter import (
    AIAdapter,
    NarrativeContext,
    NarrativeProposal,
    AIGenerationError,
    ValidationError,
)

__all__ = [
    # Version
    "__version__",
    # Models
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
    # Engine
    "CausalValidator",
    "CausalCycleError",
    "DramaticEngine",
    "DramaticVector",
    "ForcedEventType",
    "ForcedEventConstraint",
    "StateMachine",
    "StoryAdvanceResult",
    # Interfaces
    "NarrativeRepository",
    "AIAdapter",
    "NarrativeContext",
    "NarrativeProposal",
    "AIGenerationError",
    "ValidationError",
]
