"""
interfaces/ai_adapter.py — Narrative generation contract

Defines what any AI adapter connected to the CNE must return.

Implementations included in the repo:
- MockAIAdapter (Phase 1, tests without API key)
- AnthropicAdapter (Phase 3, production with Claude)
- OpenAIAdapter (Phase 3, alternative with GPT)
- LocalLLMAdapter (Phase 3, Ollama / local LLMs)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from cne_core.models.event import EntityDelta, WorldVariableDelta, DramaticDelta
from cne_core.models.commit import NarrativeChoice


@dataclass
class NarrativeContext:
    """
    The context sent to the AI to generate the next narrative.

    This is what the engine builds and passes to the AIAdapter.
    The adapter converts it into the prompt specific to each LLM.
    """
    # We import WorldDefinition and other types here to avoid circular imports
    world_definition: Any                   # Full WorldDefinition
    current_depth: int                      # Current narrative depth
    current_dramatic_state: dict[str, int]  # Current dramatic vector
    current_entity_states: dict[str, Any]   # Current entity states
    current_world_vars: dict[str, Any]      # Current global variables

    # Story so far
    commit_chain: list[Any] = field(default_factory=list)  # List of NarrativeCommit

    # Player decision (if any)
    player_choice: str | None = None

    # If there is a constraint from dramatic threshold
    forced_constraint: Any | None = None  # ForcedEventConstraint


@dataclass
class NarrativeProposal:
    """
    The proposal returned by the AI that the engine must validate.

    This is the JSON contract that the AI must respect.
    The engine validates that:
    - The entity_deltas reference existing entities
    - The dramatic_deltas are in valid range
    - The choices are coherent
    """
    narrative_text: str                      # 150-250 immersive words
    summary: str                             # 1 sentence for the trunk
    choices: list[Any]                       # List of NarrativeChoice

    # Proposed effects of the event
    entity_deltas: list[Any] = field(default_factory=list)      # list[EntityDelta]
    entity_creations: list[Any] = field(default_factory=list)   # list[EntityCreation]
    world_deltas: list[Any] = field(default_factory=list)       # list[WorldVariableDelta]
    dramatic_delta: Any = None                                   # DramaticDelta

    # Metadata
    causal_reason: str | None = None         # Why this event occurs
    is_ending: bool = False                  # Is it an ending?
    forced_event_type: str | None = None     # If forced by threshold
    raw_response: dict[str, Any] | None = None  # Raw LLM response (for logging)


class AIAdapter(ABC):
    """
    Abstract interface for AI-powered narrative generation.

    The engine calls generate_narrative() and receives a NarrativeProposal.
    It then validates the proposal and, if coherent, applies it to the state.

    Separation of responsibilities:
    - AI: generate creative and narratively rich proposals
    - Engine: validate causal coherence and state consistency
    """

    @abstractmethod
    async def generate_narrative(
        self,
        context: NarrativeContext
    ) -> NarrativeProposal:
        """
        Generates the next narrative given the current context.

        Args:
            context: Complete state of the world and the story.

        Returns:
            NarrativeProposal that the engine will validate before applying.

        Raises:
            AIGenerationError: If the AI fails or returns invalid JSON.
        """
        pass

    @abstractmethod
    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        """
        Validates and parses the raw AI response.

        Verifies that the JSON has all required fields
        and that values are in valid ranges.

        Args:
            raw_response: Raw text returned by the AI.

        Returns:
            Parsed NarrativeProposal.

        Raises:
            ValidationError: If the JSON is invalid or incomplete.
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, str]:
        """
        Returns information about the model used.

        Useful for logs and for the paper.

        Returns:
            Dict with keys: "provider", "model", "version"
        """
        pass


class AIGenerationError(Exception):
    """Error during narrative generation."""
    pass


class ValidationError(Exception):
    """Error when validating the AI response."""
    pass
