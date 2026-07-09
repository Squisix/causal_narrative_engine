"""
adapters/mock_adapter.py - Mock AIAdapter for tests

This adapter does NOT use a real AI. It generates deterministic responses
based on predefined templates.

Useful for:
- Tests that do not require API keys
- Local development without API costs
- CI/CD that does not have access to secrets
- Validating the engine flow without depending on external AI
"""

import json
import random
from typing import Optional

from cne_core.interfaces.ai_adapter import AIAdapter, NarrativeContext, NarrativeProposal
from cne_core.ai.response_schema import (
    NarrativeResponse,
    DramaticDeltaDict,
    EntityDeltaDict,
    WorldDeltaDict,
)


class MockAdapter(AIAdapter):
    """
    Mock AIAdapter that generates deterministic responses.

    Responses are generic but valid, and you can control
    their behavior with parameters.
    """

    def __init__(
        self,
        deterministic: bool = True,
        seed: int = 42,
        force_errors: bool = False,
    ):
        """
        Args:
            deterministic: If True, always generates the same response for the same input.
            seed: Seed for pseudorandom generation (if not deterministic).
            force_errors: If True, generates invalid responses for testing.
        """
        self.deterministic = deterministic
        self.seed = seed
        self.force_errors = force_errors
        self.call_count = 0

        if not deterministic:
            random.seed(seed)

    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal:
        """
        Generates a mock narrative based on the context.

        The narrative is generic but coherent with the state of the world.
        """
        self.call_count += 1

        system_prompt = "Mock system prompt (Deterministic)" if self.deterministic else "Mock system prompt (Random)"
        user_prompt = f"Mock user prompt for depth {context.current_depth} with choice {context.player_choice}"
        world_id = context.world_definition.id if hasattr(context.world_definition, "id") else "unknown"

        # If we are forcing errors, generate an invalid response
        if self.force_errors:
            proposal = self._generate_invalid_response(context)
            from adapters.logging_utils import log_ai_interaction
            log_ai_interaction(
                world_id=world_id,
                adapter_name="mock_adapter",
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                raw_response={"message": "Forced error mode enabled"},
                success=False,
                error_msg="Forced error mode enabled",
            )
            return proposal

        # Generate valid response
        proposal = self._generate_valid_response(context)

        from adapters.logging_utils import log_ai_interaction
        log_ai_interaction(
            world_id=world_id,
            adapter_name="mock_adapter",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            raw_response=proposal.raw_response if proposal.raw_response else {},
            success=True,
        )
        return proposal

    def _generate_valid_response(self, context: NarrativeContext) -> NarrativeProposal:
        """Generates a valid response using templates."""

        # Determine if this is the start of the story
        is_start = context.current_depth == 0
        is_forced = context.forced_constraint is not None

        # Narrative templates
        if is_start:
            narrative = self._generate_start_narrative(context)
        elif is_forced:
            narrative = self._generate_forced_narrative(context)
        else:
            narrative = self._generate_normal_narrative(context)

        # Generate summary
        summary = self._generate_summary(context, is_start, is_forced)

        # Generate choices (2-4 options)
        num_choices = 3 if self.deterministic else random.randint(2, 4)
        choices, tones = self._generate_choices(context, num_choices)

        # Generate dramatic deltas (based on context)
        dramatic_deltas = self._generate_dramatic_deltas(context, is_forced)

        # Entity and world deltas (empty in the simple mock)
        entity_deltas = []
        world_deltas = []

        # Causal reason
        causal_reason = self._generate_causal_reason(context, is_start)

        # Build response
        response = NarrativeResponse(
            narrative=narrative,
            summary=summary,
            choices=choices,
            choice_tones=tones,
            entity_deltas=entity_deltas,
            world_deltas=world_deltas,
            dramatic_deltas=dramatic_deltas,
            causal_reason=causal_reason,
            forced_event_type=context.forced_constraint.event_type.value if is_forced else None,
            is_ending=False,
        )

        # Convert to NarrativeProposal
        entity_deltas_core, entity_creations_core, world_deltas_core, dramatic_delta_core, choices_core = response.to_core_models()

        return NarrativeProposal(
            narrative_text=response.narrative,
            summary=response.summary,
            choices=choices_core,
            entity_deltas=entity_deltas_core,
            entity_creations=entity_creations_core,
            world_deltas=world_deltas_core,
            dramatic_delta=dramatic_delta_core,
            causal_reason=response.causal_reason,
            is_ending=response.is_ending,
            raw_response=response.model_dump(),
        )

    def _generate_start_narrative(self, context: NarrativeContext) -> str:
        """Generates start narrative."""
        world_name = context.world_definition.name
        protagonist = context.world_definition.protagonist
        tone = context.world_definition.tone.value

        return f"""The story of {world_name} begins. {protagonist} finds themselves at a crucial moment. The atmosphere is {tone}, and the decisions made now will determine the course of events to come. Everything is calm, but tension can be felt in the air. It is time to act."""

    def _generate_forced_narrative(self, context: NarrativeContext) -> str:
        """Generates narrative for a forced event."""
        event_type = context.forced_constraint.event_type.value
        description = context.forced_constraint.description

        return f"""[FORCED EVENT: {event_type}] {description} The situation has reached a critical point. There is no turning back. The events that led to this moment now culminate in a direct confrontation with the forces at play. The tension is palpable, and the consequences of what happens next will resonate throughout the entire story."""

    def _generate_normal_narrative(self, context: NarrativeContext) -> str:
        """Generates normal narrative."""
        choice_text = context.player_choice if context.player_choice else "a decision"

        narratives = [
            f"""Having chosen {choice_text}, events unfold in unexpected ways. The decision made has ramifications that extend beyond what is immediately visible. New opportunities open up, but new dangers also lurk in the shadows. It is time to carefully consider the next step.""",

            f"""The choice of {choice_text} reverberates through the events. The consequences manifest in both subtle and evident ways. Some paths close while others are revealed. The story moves forward, carrying with it the weight of past decisions and the promise of future ones.""",

            f"""After {choice_text}, the world responds. The echoes of this action extend, touching lives and altering destinies. What seemed clear now becomes complex. New questions emerge, demanding attention. The path ahead requires wisdom and courage.""",
        ]

        if self.deterministic:
            return narratives[self.call_count % len(narratives)]
        else:
            return random.choice(narratives)

    def _generate_summary(self, context: NarrativeContext, is_start: bool, is_forced: bool) -> str:
        """Generates a one-line summary."""
        if is_start:
            return f"The story of {context.world_definition.name} begins."

        if is_forced:
            event_type = context.forced_constraint.event_type.value
            return f"Forced event: {event_type} occurs as a consequence of previous decisions."

        choice = context.player_choice if context.player_choice else "an action"
        return f"After {choice}, new events unfold and options emerge."

    def _generate_choices(self, context: NarrativeContext, num: int) -> tuple[list[str], list[str]]:
        """Generates choices and their tone hints."""
        choice_templates = [
            ("Act with caution and observe", "cautious"),
            ("Take direct and immediate action", "confrontational"),
            ("Seek allies before proceeding", "diplomatic"),
            ("Explore non-obvious alternatives", "creative"),
            ("Wait and gather more information", "patient"),
        ]

        selected = choice_templates[:num]
        choices = [c[0] for c in selected]
        tones = [c[1] for c in selected]

        return choices, tones

    def _generate_dramatic_deltas(self, context: NarrativeContext, is_forced: bool) -> DramaticDeltaDict:
        """Generates dramatic deltas based on context."""
        if is_forced:
            # Forced event: large impact
            event_type = context.forced_constraint.event_type.value
            if event_type == "CLIMAX":
                return DramaticDeltaDict(tension=25, hope=-10, saturation=20)
            elif event_type == "TRAGEDY":
                return DramaticDeltaDict(tension=15, hope=-30, connection=-10)
            else:
                return DramaticDeltaDict(tension=10, hope=-5, chaos=10)
        else:
            # Normal event: moderate impact
            return DramaticDeltaDict(
                tension=5,
                hope=0,
                chaos=2,
                saturation=3,
            )

    def _generate_causal_reason(self, context: NarrativeContext, is_start: bool) -> str:
        """Generates the causal reason."""
        if is_start:
            return "This is the initial event that establishes the state of the world."

        if context.player_choice:
            return f"This event occurs as a direct consequence of the decision: {context.player_choice}"

        return "This event is a natural continuation of previous events."

    def _generate_invalid_response(self, context: NarrativeContext) -> NarrativeProposal:
        """Generates an invalid response for testing error handling."""
        # Create an invalid response WITHOUT using Pydantic (to bypass validation)
        # This simulates what would happen if the AI returns invalid JSON
        from cne_core.models.event import DramaticDelta

        return NarrativeProposal(
            narrative_text="Too short",  # Too short, < 50 characters
            summary="X",  # Too short, < 10 characters
            choices=[],  # No choices (invalid)
            entity_deltas=[],
            world_deltas=[],
            dramatic_delta=DramaticDelta(tension=0, hope=0, chaos=0),
            causal_reason="Error forced",
            is_ending=False,
            raw_response={"error": "forced_error_mode"},
        )

    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        """
        Validates and parses the response (not used in mock, always returns mock data).

        In a real adapter, this would parse JSON and validate with Pydantic.
        In the mock, it simply generates a mock response.
        """
        # The mock does not use raw_response, it generates directly
        # This method exists only to comply with the interface
        return await self._generate_valid_response(
            NarrativeContext(
                world_definition=None,  # Not used in mock validation
                current_depth=0,
                current_dramatic_state={},
                current_entity_states={},
                current_world_vars={},
                commit_chain=[],
                player_choice=None,
                forced_constraint=None,
            )
        )

    def get_model_info(self) -> dict[str, str]:
        """Returns model information (mock)."""
        return {
            "provider": "Mock",
            "model": "Deterministic" if self.deterministic else "Random",
            "version": f"seed-{self.seed}",
        }

    def get_stats(self) -> dict:
        """Returns mock adapter statistics."""
        return {
            "total_calls": self.call_count,
            "deterministic": self.deterministic,
            "force_errors": self.force_errors,
        }
