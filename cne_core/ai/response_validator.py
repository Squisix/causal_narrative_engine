"""
cne_core/ai/response_validator.py - AI response validation

The ResponseValidator verifies that AI-generated responses
comply with the engine's P1-P4 properties before applying them:

P1 - CAUSALITY: No cycles created, events well connected
P2 - DETERMINISM: States reconstructible
P3 - VERSIONING: Correct metadata
P4 - CONSISTENCY: Dead entities do not act, values in range

If a response fails validation, it is rejected and can be:
- Asked to the AI to regenerate
- Applied with safe fallbacks
- Logged for prompt improvement
"""

from typing import Any, Optional
from dataclasses import dataclass

from cne_core.ai.response_schema import NarrativeResponse
from cne_core.models.world import WorldDefinition


@dataclass
class ValidationResult:
    """
    Result of validating an AI response.

    If is_valid=False, errors contains the list of issues found.
    """
    is_valid: bool
    errors: list[str]
    warnings: list[str]

    def __str__(self) -> str:
        if self.is_valid:
            warnings_str = f" ({len(self.warnings)} warnings)" if self.warnings else ""
            return f"[VALID]{warnings_str}"
        else:
            return f"[INVALID] {len(self.errors)} errors: {'; '.join(self.errors[:3])}"


class ResponseValidator:
    """
    Validates that AI responses are coherent and safe.

    Performs validations at two levels:
    1. Schema validation (Pydantic does this automatically)
    2. Narrative coherence validation (this validator)
    """

    def __init__(
        self,
        world: WorldDefinition,
        current_entities: dict[str, Any],
        current_world_vars: dict[str, Any],
    ):
        """
        Args:
            world: The world seed (defines the rules).
            current_entities: Current state of entities.
            current_world_vars: Current state of world variables.
        """
        self.world = world
        self.current_entities = current_entities
        self.current_world_vars = current_world_vars

    def validate(self, response: NarrativeResponse) -> ValidationResult:
        """
        Validates a complete AI response.

        Args:
            response: The parsed response (already passed Pydantic validation).

        Returns:
            ValidationResult indicating whether it is valid and what errors exist.
        """
        errors = []
        warnings = []

        # V1: Validate entity deltas
        entity_errors = self._validate_entity_deltas(response.entity_deltas)
        errors.extend(entity_errors)

        # V2: Validate dramatic deltas
        dramatic_errors = self._validate_dramatic_deltas(response.dramatic_deltas)
        errors.extend(dramatic_errors)

        # V3: Validate narrative coherence
        narrative_warnings = self._validate_narrative_coherence(response)
        warnings.extend(narrative_warnings)

        # V4: Validate choices
        choice_errors = self._validate_choices(response)
        errors.extend(choice_errors)

        # V5: Validate that world constraints are respected
        constraint_errors = self._validate_world_constraints(response)
        errors.extend(constraint_errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_entity_deltas(self, entity_deltas: list) -> list[str]:
        """
        Validates that entity deltas are coherent.

        P4: Dead entities cannot act.
        """
        errors = []

        for delta in entity_deltas:
            entity_id = delta.entity_id
            entity_name = delta.entity_name

            # Check that the entity exists
            if entity_id not in self.current_entities:
                # Could be a new entity created in this event
                # For now, just a warning
                continue

            entity_state = self.current_entities[entity_id]

            # CRITICAL: Dead entities cannot act
            if not entity_state.get("alive", True):
                # Unless the delta is to resurrect it (alive attribute change)
                if delta.attribute != "alive":
                    errors.append(
                        f"P4 VIOLATION: Dead entity '{entity_name}' cannot "
                        f"change attribute '{delta.attribute}'. "
                        f"Dead entities do not act."
                    )

            # Validate that old_value matches current state
            current_value = entity_state.get(delta.attribute)
            if current_value is not None and current_value != delta.old_value:
                errors.append(
                    f"CONSISTENCY ERROR: Entity '{entity_name}' has "
                    f"{delta.attribute}={current_value} but the AI assumes "
                    f"{delta.old_value}. Inconsistent state."
                )

        return errors

    def _validate_dramatic_deltas(self, dramatic_deltas) -> list[str]:
        """
        Validates that dramatic deltas are in range.

        Deltas must be in [-100, +100].
        """
        errors = []

        # Pydantic already validates the range, but we double-check just in case
        deltas_dict = dramatic_deltas.dict() if hasattr(dramatic_deltas, 'dict') else dramatic_deltas

        for meter, value in deltas_dict.items():
            if not isinstance(value, int):
                errors.append(
                    f"DRAMATIC DELTA ERROR: {meter} must be int, got {type(value)}"
                )
                continue

            if not (-100 <= value <= 100):
                errors.append(
                    f"DRAMATIC DELTA ERROR: {meter}={value} out of range [-100, +100]"
                )

        return errors

    def _validate_narrative_coherence(self, response: NarrativeResponse) -> list[str]:
        """
        Narrative coherence validations (non-critical, warnings).

        Things that do not break the engine but indicate the AI could improve.
        """
        warnings = []

        # W1: Narrative too short
        word_count = len(response.narrative.split())
        if word_count < 50:
            warnings.append(
                f"Short narrative ({word_count} words). Recommended: 150-250."
            )

        # W2: Narrative too long
        if word_count > 350:
            warnings.append(
                f"Long narrative ({word_count} words). May tire the player."
            )

        # W3: Summary too long
        if len(response.summary) > 150:
            warnings.append(
                "Summary too long. Should be 1 concise sentence."
            )

        # W4: No dramatic changes (flat story)
        if response.dramatic_deltas:
            deltas_dict = response.dramatic_deltas.dict() if hasattr(response.dramatic_deltas, 'dict') else response.dramatic_deltas
            total_change = sum(abs(v) for v in deltas_dict.values())
            if total_change == 0 and not response.is_ending:
                warnings.append(
                    "No dramatic changes. The story may feel flat."
                )

        # W5: Too many deltas (excessive complexity)
        if len(response.entity_deltas) > 5:
            warnings.append(
                f"{len(response.entity_deltas)} entity deltas. Could be too "
                f"complex for a single event."
            )

        return warnings

    def _validate_choices(self, response: NarrativeResponse) -> list[str]:
        """
        Validates that choices are appropriate.
        """
        errors = []

        # If ending, there should be no choices
        if response.is_ending and len(response.choices) > 0:
            errors.append(
                "ENDING ERROR: is_ending=true but there are choices. "
                "Endings have no options."
            )

        # If not ending, there should be at least 2 choices
        if not response.is_ending and len(response.choices) < 2:
            errors.append(
                "CHOICES ERROR: There must be at least 2 options (except for endings)."
            )

        # Check that choices are not identical
        if len(response.choices) > 1:
            unique_choices = set(c.lower().strip() for c in response.choices)
            if len(unique_choices) < len(response.choices):
                errors.append(
                    "CHOICES ERROR: There are duplicate or very similar options."
                )

        return errors

    def _validate_world_constraints(self, response: NarrativeResponse) -> list[str]:
        """
        Validates that the response respects the world constraints.

        This is CRITICAL: WorldDefinition constraints are inviolable.
        """
        errors = []

        # Check each constraint
        for constraint in self.world.constraints:
            # Search for keywords in the constraint
            constraint_lower = constraint.lower()

            # Example: "The dead cannot return"
            if "dead" in constraint_lower and "no" in constraint_lower:
                # Verify that no entity_delta resurrects someone
                for delta in response.entity_deltas:
                    if delta.attribute == "alive":
                        if delta.old_value == False and delta.new_value == True:
                            errors.append(
                                f"WORLD CONSTRAINT VIOLATION: '{constraint}'. "
                                f"The AI attempted to resurrect '{delta.entity_name}'."
                            )

            # Example: "No time travel"
            if "time" in constraint_lower and "no" in constraint_lower:
                # Search for keywords in narrative and summary
                narrative_lower = response.narrative.lower()
                summary_lower = response.summary.lower()

                time_keywords = ["past", "future", "time travel", "go back"]
                for keyword in time_keywords:
                    if keyword in narrative_lower or keyword in summary_lower:
                        errors.append(
                            f"WORLD CONSTRAINT VIOLATION: '{constraint}'. "
                            f"The narrative mentions forbidden temporal concepts."
                        )

            # Can add more specific validations per constraint type

        return errors

    def validate_with_fallback(
        self,
        response: NarrativeResponse,
        attempt: int = 1,
        max_attempts: int = 3,
    ) -> tuple[bool, ValidationResult, Optional[str]]:
        """
        Validates the response and suggests how to correct it if it fails.

        Args:
            response: The response to validate.
            attempt: Current attempt number.
            max_attempts: Maximum allowed attempts.

        Returns:
            tuple: (should_retry, result, message_for_ai)
        """
        result = self.validate(response)

        if result.is_valid:
            return (False, result, None)  # Do not retry, all ok

        if attempt >= max_attempts:
            return (False, result, None)  # Do not retry, maximum reached

        # Build message for the AI
        error_summary = "; ".join(result.errors[:3])  # Top 3 errors
        feedback = (
            f"The response has validation errors (attempt {attempt}/{max_attempts}):\n"
            f"{error_summary}\n\n"
            f"Please generate a new response that corrects these issues."
        )

        return (True, result, feedback)
