"""
cne_core/ai/response_schema.py - AI response schema

Defines the JSON contract that the AI must return using Pydantic.
This guarantees that responses are valid and can be processed
by the engine without errors.

Expected response example:
{
  "narrative": "Immersive text of 150-250 words...",
  "summary": "1-sentence causal summary",
  "choices": ["option A", "option B", "option C"],
  "choice_dramatic_preview": [
    {"choice": "option A", "tension_delta": 15, "hope_delta": -10, "tone": "confrontational"},
    {"choice": "option B", "tension_delta": -5, "hope_delta": 5, "tone": "diplomatic"},
    {"choice": "option C", "tension_delta": 5, "hope_delta": 10, "tone": "unexpected"}
  ],
  "entity_deltas": [
    {"entity_id": "uuid", "entity_name": "Lyra", "attribute": "health", "old_value": 100, "new_value": 85}
  ],
  "world_deltas": [
    {"variable": "political_stability", "old_value": 60, "new_value": 48}
  ],
  "dramatic_deltas": {
    "tension": 15, "hope": -8, "chaos": 5,
    "rhythm": 0, "saturation": 8, "connection": -3, "mystery": 10
  },
  "causal_reason": "Why this event occurs given the current state",
  "forced_event_type": null,
  "is_ending": false
}
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class DramaticDeltaDict(BaseModel):
    """
    Changes in the dramatic vector proposed by the AI.

    Each value must be in the range [-100, +100].
    A value of 0 means "no change".
    """
    tension: int = Field(default=0, ge=-100, le=100)
    hope: int = Field(default=0, ge=-100, le=100)
    chaos: int = Field(default=0, ge=-100, le=100)
    rhythm: int = Field(default=0, ge=-100, le=100)
    saturation: int = Field(default=0, ge=-100, le=100)
    connection: int = Field(default=0, ge=-100, le=100)
    mystery: int = Field(default=0, ge=-100, le=100)

    def to_dramatic_delta(self):
        """Converts to core DramaticDelta."""
        from cne_core.models.event import DramaticDelta
        return DramaticDelta(
            tension=self.tension,
            hope=self.hope,
            chaos=self.chaos,
            rhythm=self.rhythm,
            saturation=self.saturation,
            connection=self.connection,
            mystery=self.mystery,
        )


class EntityDeltaDict(BaseModel):
    """
    Change in an attribute of an entity.

    The AI must specify entity_id (UUID), entity_name (for validation),
    the attribute that changes, and the old/new values.
    """
    entity_id: str = Field(..., description="Entity UUID")
    entity_name: str = Field(..., description="Entity name (for validation)")
    attribute: str = Field(..., description="Name of the attribute that changes")
    old_value: Any = Field(..., description="Previous value")
    new_value: Any = Field(..., description="New value")

    def to_entity_delta(self):
        """Converts to core EntityDelta."""
        from cne_core.models.event import EntityDelta
        return EntityDelta(
            entity_id=self.entity_id,
            entity_name=self.entity_name,
            attribute=self.attribute,
            old_value=self.old_value,
            new_value=self.new_value,
        )


class EntityCreationDict(BaseModel):
    """
    Creation of a new entity proposed by the AI.

    The AI specifies name, type, and initial attributes.
    The engine assigns the UUID and created_at_depth automatically.
    """
    entity_name: str = Field(..., description="Name of the new entity")
    entity_type: str = Field(
        ...,
        description="Type: character, faction, artifact, location"
    )
    attributes: dict[str, Any] = Field(
        default_factory=dict,
        description="Initial attributes (e.g., {health: 100, possessed_by: null})"
    )

    @field_validator('entity_type')
    @classmethod
    def validate_entity_type(cls, v):
        valid_types = {"character", "faction", "artifact", "location"}
        if v.lower() not in valid_types:
            raise ValueError(f"entity_type must be one of {valid_types}, received: '{v}'")
        return v.lower()

    def to_entity_creation(self):
        """Converts to core EntityCreation."""
        from cne_core.models.event import EntityCreation
        return EntityCreation(
            entity_name=self.entity_name,
            entity_type=self.entity_type,
            attributes=self.attributes,
        )


class WorldDeltaDict(BaseModel):
    """
    Change in a global world variable.
    """
    variable: str = Field(..., description="Variable name")
    old_value: Any = Field(..., description="Previous value")
    new_value: Any = Field(..., description="New value")

    def to_world_delta(self):
        """Converts to core WorldVariableDelta."""
        from cne_core.models.event import WorldVariableDelta
        return WorldVariableDelta(
            variable=self.variable,
            old_value=self.old_value,
            new_value=self.new_value,
        )


class ChoicePreview(BaseModel):
    """
    Preview of the estimated dramatic impact of an option.

    This helps the player understand the potential consequences
    of each decision before making it.
    """
    choice: str = Field(..., description="Option text")
    tension_delta: int = Field(default=0, ge=-50, le=50, description="Estimated change in tension")
    hope_delta: int = Field(default=0, ge=-50, le=50, description="Estimated change in hope")
    chaos_delta: int = Field(default=0, ge=-50, le=50, description="Estimated change in chaos")
    tone: str = Field(default="neutral", description="Tone of the option (confrontational, diplomatic, etc.)")

    def to_narrative_choice(self):
        """Converts to core NarrativeChoice."""
        from cne_core.models.commit import NarrativeChoice
        return NarrativeChoice(
            text=self.choice,
            dramatic_preview={
                "tension": self.tension_delta,
                "hope": self.hope_delta,
                "chaos": self.chaos_delta,
            },
            tone_hint=self.tone,
        )


class NarrativeResponse(BaseModel):
    """
    Complete AI response.

    This is the schema that the AI must follow mandatorily.
    The ResponseValidator will verify that everything is coherent before
    applying it to the engine.
    """
    # Narrative
    narrative: str = Field(
        ...,
        min_length=50,
        max_length=2000,
        description="Immersive narrative text (150-250 words recommended)"
    )

    summary: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description="1-sentence causal summary for the active trunk"
    )

    # Player options
    choices: list[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Available options for the player (2-5 options)"
    )

    choice_dramatic_preview: list[ChoicePreview] = Field(
        default_factory=list,
        description="Preview of the impact of each option"
    )

    # State deltas
    entity_deltas: list[EntityDeltaDict] = Field(
        default_factory=list,
        description="Entity changes caused by this event"
    )

    entity_creations: list[EntityCreationDict] = Field(
        default_factory=list,
        description="New entities created during this event"
    )

    world_deltas: list[WorldDeltaDict] = Field(
        default_factory=list,
        description="Changes in global world variables"
    )

    dramatic_deltas: DramaticDeltaDict = Field(
        default_factory=DramaticDeltaDict,
        description="Changes in the dramatic vector"
    )

    # Metadata
    causal_reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Why this event occurs given the current state"
    )

    forced_event_type: Optional[str] = Field(
        default=None,
        description="If there is a forced event, its type (CLIMAX, TRAGEDY, etc.)"
    )

    is_ending: bool = Field(
        default=False,
        description="Is this the end of the story?"
    )

    @field_validator('choice_dramatic_preview')
    @classmethod
    def validate_preview_matches_choices(cls, v, info):
        """Verifies that there is a preview for each choice."""
        if 'choices' in info.data:
            choices = info.data['choices']
            if len(v) > 0 and len(v) != len(choices):
                raise ValueError(
                    f"There must be {len(choices)} previews, one per option. "
                    f"Found: {len(v)}"
                )
            # Verify that the texts match
            if v:
                preview_texts = {p.choice for p in v}
                choice_texts = set(choices)
                if preview_texts != choice_texts:
                    raise ValueError(
                        f"The option texts do not match between choices and preview"
                    )
        return v

    @field_validator('narrative')
    @classmethod
    def validate_narrative_length(cls, v):
        """Verifies that the narrative has a reasonable length."""
        word_count = len(v.split())
        if word_count < 30:
            raise ValueError(
                f"The narrative is too short ({word_count} words). "
                f"Minimum recommended: 50 words."
            )
        if word_count > 400:
            raise ValueError(
                f"The narrative is too long ({word_count} words). "
                f"Maximum recommended: 250 words."
            )
        return v

    @field_validator('is_ending')
    @classmethod
    def validate_ending_has_no_choices(cls, v, info):
        """If it is the ending, there should be no choices."""
        if v and 'choices' in info.data:
            choices = info.data['choices']
            if len(choices) > 0:
                raise ValueError(
                    "If is_ending=true, there should be no choices. "
                    "The ending has no more decisions."
                )
        return v

    def to_core_models(self):
        """
        Converts the response to core models.

        Returns:
            tuple: (entity_deltas, entity_creations, world_deltas, dramatic_delta, choices)
        """
        entity_deltas = [d.to_entity_delta() for d in self.entity_deltas]
        entity_creations = [c.to_entity_creation() for c in self.entity_creations]
        world_deltas = [d.to_world_delta() for d in self.world_deltas]
        dramatic_delta = self.dramatic_deltas.to_dramatic_delta()

        if self.choice_dramatic_preview:
            choices = [p.to_narrative_choice() for p in self.choice_dramatic_preview]
        else:
            from cne_core.models.commit import NarrativeChoice
            choices = [NarrativeChoice(text=c) for c in self.choices]

        return entity_deltas, entity_creations, world_deltas, dramatic_delta, choices

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "narrative": "The throne room falls silent as Lyra receives the news...",
                "summary": "King Aldric dies mysteriously. Lyra takes the throne.",
                "choices": [
                    "Confront Malachar directly",
                    "Order a secret investigation",
                    "Accept Malachar's 'help'"
                ],
                "choice_dramatic_preview": [
                    {
                        "choice": "Confront Malachar directly",
                        "tension_delta": 15,
                        "hope_delta": -5,
                        "tone": "confrontational"
                    },
                    {
                        "choice": "Order a secret investigation",
                        "tension_delta": 5,
                        "hope_delta": 5,
                        "tone": "cautious"
                    },
                    {
                        "choice": "Accept Malachar's 'help'",
                        "tension_delta": -5,
                        "hope_delta": -10,
                        "tone": "submissive"
                    }
                ],
                "entity_deltas": [],
                "world_deltas": [],
                "dramatic_deltas": {
                    "tension": 10,
                    "hope": -5,
                    "chaos": 5,
                    "rhythm": 0,
                    "saturation": 2,
                    "connection": 5,
                    "mystery": 10
                },
                "causal_reason": "The king's death is the triggering event that initiates the conflict",
                "forced_event_type": None,
                "is_ending": False
            }
        }
    )
