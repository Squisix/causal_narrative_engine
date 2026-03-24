"""
interfaces/ai_adapter.py — Contrato de generación narrativa

Define qué debe retornar cualquier adaptador de IA que se conecte al CNE.

Implementaciones incluidas en el repo:
- MockAIAdapter (Fase 1 ✅, tests sin API key)
- AnthropicAdapter (Fase 3, producción con Claude)
- OpenAIAdapter (Fase 3, alternativa con GPT)
- LocalLLMAdapter (Fase 3, Ollama / LLMs locales)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from cne_core.models.event import EntityDelta, WorldVariableDelta, DramaticDelta
from cne_core.models.commit import NarrativeChoice


@dataclass
class NarrativeContext:
    """
    El contexto que se envía a la IA para generar la próxima narrativa.

    Esto es lo que el motor construye y pasa al AIAdapter.
    El adapter lo convierte en el prompt específico de cada LLM.
    """
    # Importamos WorldDefinition y otros types aquí para evitar circular imports
    world_definition: Any                   # WorldDefinition completo
    current_depth: int                      # Profundidad narrativa actual
    current_dramatic_state: dict[str, int]  # Vector dramático actual
    current_entity_states: dict[str, Any]   # Estado actual de entidades
    current_world_vars: dict[str, Any]      # Variables globales actuales

    # Historia hasta ahora
    commit_chain: list[Any] = field(default_factory=list)  # Lista de NarrativeCommit

    # Decisión del jugador (si hay)
    player_choice: str | None = None

    # Si hay constraint por umbral dramático
    forced_constraint: Any | None = None  # ForcedEventConstraint


@dataclass
class NarrativeProposal:
    """
    La propuesta que retorna la IA y que el motor debe validar.

    Este es el contrato JSON que la IA debe respetar.
    El motor valida que:
    - Los entity_deltas referencien entidades existentes
    - Los dramatic_deltas estén en rango válido
    - Las choices sean coherentes
    """
    narrative_text: str                      # 150-250 palabras inmersivas
    summary: str                             # 1 oración para el tronco
    choices: list[Any]                       # Lista de NarrativeChoice

    # Efectos propuestos del evento
    entity_deltas: list[Any] = field(default_factory=list)  # list[EntityDelta]
    world_deltas: list[Any] = field(default_factory=list)   # list[WorldVariableDelta]
    dramatic_delta: Any = None                               # DramaticDelta

    # Metadata
    causal_reason: str | None = None         # Por qué ocurre este evento
    is_ending: bool = False                  # ¿Es un final?
    forced_event_type: str | None = None     # Si fue forzado por umbral
    raw_response: dict[str, Any] | None = None  # Respuesta cruda del LLM (para logging)


class AIAdapter(ABC):
    """
    Interfaz abstracta para generación narrativa con IA.

    El motor llama a generate_narrative() y recibe un NarrativeProposal.
    Luego valida la propuesta y, si es coherente, la aplica al estado.

    Separación de responsabilidades:
    - IA: generar propuestas creativas y narrativamente ricas
    - Motor: validar coherencia causal y consistencia de estado
    """

    @abstractmethod
    async def generate_narrative(
        self,
        context: NarrativeContext
    ) -> NarrativeProposal:
        """
        Genera la próxima narrativa dado el contexto actual.

        Args:
            context: Estado completo del mundo y la historia.

        Returns:
            NarrativeProposal que el motor validará antes de aplicar.

        Raises:
            AIGenerationError: Si la IA falla o retorna JSON inválido.
        """
        pass

    @abstractmethod
    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        """
        Valida y parsea la respuesta cruda de la IA.

        Verifica que el JSON tenga todos los campos requeridos
        y que los valores estén en rangos válidos.

        Args:
            raw_response: Texto crudo retornado por la IA.

        Returns:
            NarrativeProposal parseado.

        Raises:
            ValidationError: Si el JSON es inválido o incompleto.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, str]:
        """
        Retorna información del modelo usado.

        Útil para logs y para el paper.

        Returns:
            Dict con keys: "provider", "model", "version"
        """
        pass


class AIGenerationError(Exception):
    """Error durante generación narrativa."""
    pass


class ValidationError(Exception):
    """Error al validar la respuesta de la IA."""
    pass
