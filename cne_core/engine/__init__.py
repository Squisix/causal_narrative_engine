"""
cne_core/engine — Narrative engine components

The engine is composed of:
- CausalValidator: Validates that the event graph is a cycle-free DAG
- DramaticEngine: Manages the 7-meter vector and evaluates thresholds
- StateMachine: Orchestrator that coordinates validation, state, and progression
"""

from cne_core.engine.causal_validator import CausalValidator, CausalCycleError
from cne_core.engine.dramatic_engine import (
    DramaticEngine,
    DramaticVector,
    ForcedEventType,
    ForcedEventConstraint,
)
from cne_core.engine.state_machine import StateMachine, StoryAdvanceResult

__all__ = [
    "CausalValidator",
    "CausalCycleError",
    "DramaticEngine",
    "DramaticVector",
    "ForcedEventType",
    "ForcedEventConstraint",
    "StateMachine",
    "StoryAdvanceResult",
]
