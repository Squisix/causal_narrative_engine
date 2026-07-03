"""
cne_core — Causal Narrative Engine Core

The standalone narrative engine. Can be used without external dependencies
(Phase 1 in-memory) or with PostgreSQL (Phase 2).

Main exports:
- WorldDefinition, Entity, NarrativeTone
- NarrativeEvent, EventType, DramaticDelta
- NarrativeCommit, Branch
- CausalValidator, DramaticEngine, StateMachine

Interfaces:
- NarrativeRepository (for persistence)
- AIAdapter (for narrative generation)
"""

__version__ = "0.3.0"

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
