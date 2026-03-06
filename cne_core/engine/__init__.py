"""
cne_core/engine — Componentes del motor narrativo

El motor se compone de:
- CausalValidator: Valida que el grafo de eventos sea un DAG sin ciclos
- DramaticEngine: Gestiona el vector de 7 medidores y evalúa umbrales
- StateMachine: Orquestador que coordina validación, estado y progresión
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
