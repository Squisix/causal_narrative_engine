"""
api/models/requests.py - Request schemas

Schemas de Pydantic para validar requests del cliente.
"""

from pydantic import BaseModel, Field
from typing import Optional


class EntityRequest(BaseModel):
    """Entidad inicial para un mundo."""
    name: str = Field(..., min_length=1, max_length=200)
    entity_type: str = Field(default="character", description="character, location, artifact, faction")
    attributes: dict = Field(default_factory=dict, description="Atributos iniciales (ej: {health: 100, mood: 'neutral'})")


class CreateWorldRequest(BaseModel):
    """
    Request para crear un nuevo mundo (semilla).

    POST /worlds
    """
    name: str = Field(..., min_length=3, max_length=200, description="Nombre del mundo")
    context: str = Field(..., min_length=10, max_length=2000, description="Descripción del universo narrativo")
    protagonist: str = Field(..., min_length=2, max_length=200, description="Nombre del protagonista")
    era: str = Field(..., min_length=2, max_length=200, description="Época o ambientación")
    tone: str = Field(..., description="Tono narrativo (epic, dark, mysterious, adventurous, philosophical, black_humor)")

    antagonist: Optional[str] = Field(default="desconocido", max_length=500)
    rules: Optional[str] = Field(default="El mundo sigue sus propias leyes", max_length=1000)
    constraints: list[str] = Field(default_factory=list, description="Restricciones narrativas absolutas")

    initial_entities: list[EntityRequest] = Field(
        default_factory=list,
        description="Entidades iniciales del mundo (personajes, locaciones, items)"
    )

    # Configuración dramática inicial
    dramatic_config: Optional[dict[str, int]] = Field(
        default=None,
        description="Valores iniciales del vector dramático (tension, hope, chaos, etc.)"
    )

    max_depth: int = Field(default=0, ge=0, description="Máximo de decisiones antes de forzar final (0 = ilimitado)")

    class Config:
        json_schema_extra = {
            "example": {
                "name": "Reino de Valdris",
                "context": "Un reino medieval al borde de la guerra. El rey ha muerto misteriosamente.",
                "protagonist": "Lyra, la princesa heredera",
                "era": "Medieval fantástico, año 843",
                "tone": "dark",
                "antagonist": "Malachar, el consejero corrupto",
                "rules": "La magia existe pero tiene un precio en sangre",
                "constraints": ["No puede haber viajes en el tiempo", "Los muertos no resucitan"],
                "dramatic_config": {
                    "tension": 30,
                    "hope": 60,
                    "chaos": 20,
                    "rhythm": 50,
                    "saturation": 0,
                    "connection": 40,
                    "mystery": 50
                },
                "max_depth": 20
            }
        }


class StartNarrativeRequest(BaseModel):
    """
    Request para iniciar la narrativa en un mundo.

    POST /worlds/{world_id}/start
    """
    adapter_type: str = Field(
        default="mock",
        description="Tipo de AI adapter ('mock' o 'anthropic')"
    )

    adapter_config: Optional[dict] = Field(
        default=None,
        description="Configuración específica del adapter (API keys, modelo, etc.)"
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
    Request para avanzar la narrativa tomando una decisión.

    POST /commits/{commit_id}/advance
    """
    choice: str = Field(..., min_length=1, max_length=500, description="Texto de la opción elegida")

    custom: bool = Field(
        default=False,
        description="True si es una opción escrita por el jugador (salta validación de choices)"
    )

    adapter_type: str = Field(
        default="ollama",
        description="Tipo de AI adapter ('mock', 'anthropic' o 'ollama')"
    )

    adapter_config: Optional[dict] = Field(
        default=None,
        description="Configuración específica del adapter"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "choice": "Confrontar a Malachar directamente",
                "adapter_type": "ollama"
            }
        }
