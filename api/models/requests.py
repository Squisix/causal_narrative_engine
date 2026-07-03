"""
api/models/requests.py - Request schemas

Pydantic schemas to validate client requests.
"""

from pydantic import BaseModel, Field
from typing import Optional


class EntityRequest(BaseModel):
    """Initial entity for a world."""
    name: str = Field(..., min_length=1, max_length=200)
    entity_type: str = Field(default="character", description="character, location, artifact, faction")
    attributes: dict = Field(default_factory=dict, description="Initial attributes (e.g., {health: 100, mood: 'neutral'})")


class CreateWorldRequest(BaseModel):
    """
    Request to create a new world (seed).

    POST /worlds
    """
    name: str = Field(..., min_length=3, max_length=200, description="Name of the world")
    context: str = Field(..., min_length=10, max_length=2000, description="Description of the narrative universe")
    protagonist: str = Field(..., min_length=2, max_length=200, description="Name of the protagonist")
    era: str = Field(..., min_length=2, max_length=200, description="Era or setting")
    tone: str = Field(..., description="Narrative tone (epic, dark, mysterious, adventurous, philosophical, black_humor)")

    antagonist: Optional[str] = Field(default="unknown", max_length=500)
    rules: Optional[str] = Field(default="The world follows its own laws", max_length=1000)
    constraints: list[str] = Field(default_factory=list, description="Absolute narrative constraints")

    initial_entities: list[EntityRequest] = Field(
        default_factory=list,
        description="Initial entities in the world (characters, locations, items)"
    )

    # Initial dramatic configuration
    dramatic_config: Optional[dict[str, int]] = Field(
        default=None,
        description="Initial values of the dramatic vector (tension, hope, chaos, etc.)"
    )

    max_depth: int = Field(default=0, ge=0, description="Maximum depth before forcing an ending (0 = unlimited)")
    output_language: str = Field(default="es", description="Language of the generated narrative (e.g., 'es', 'en', 'fr')")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Kingdom of Valdris",
                "context": "A medieval kingdom on the brink of war. The king has died mysteriously.",
                "protagonist": "Lyra, the crown princess",
                "era": "Medieval fantasy, year 843",
                "tone": "dark",
                "antagonist": "Malachar, the corrupt counselor",
                "rules": "Magic exists but has a price in blood",
                "constraints": ["No time travel allowed", "The dead do not resurrect"],
                "dramatic_config": {
                    "tension": 30,
                    "hope": 60,
                    "chaos": 20,
                    "rhythm": 50,
                    "saturation": 0,
                    "connection": 40,
                    "mystery": 50
                },
                "max_depth": 20,
                "output_language": "es"
            }
        }


class StartNarrativeRequest(BaseModel):
    """
    Request to start the narrative in a world.

    POST /worlds/{world_id}/start
    """
    adapter_type: str = Field(
        default="mock",
        description="Type of AI adapter ('mock' or 'anthropic')"
    )

    adapter_config: Optional[dict] = Field(
        default=None,
        description="Adapter-specific configuration (API keys, model, etc.)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "adapter_type": "mock",
                "adapter_config": {
                    "deterministic": True,
                    "seed": 42
                }
            }
        }


class AdvanceNarrativeRequest(BaseModel):
    """
    Request to advance the narrative by making a choice.

    POST /commits/{commit_id}/advance
    """
    choice: str = Field(..., min_length=1, max_length=500, description="Text of the chosen option")

    custom: bool = Field(
        default=False,
        description="True if it is a custom choice written by the player (skips available choices validation)"
    )

    adapter_type: str = Field(
        default="mock",
        description="Type of AI adapter ('mock', 'anthropic' or 'ollama')"
    )

    adapter_config: Optional[dict] = Field(
        default=None,
        description="Adapter-specific configuration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "choice": "Confront Malachar directly",
                "adapter_type": "mock"
            }
        }
