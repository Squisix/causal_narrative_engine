"""
api/models - Request/Response schemas

Schemas de Pydantic para validación automática de la API.
"""

from api.models.requests import (
    CreateWorldRequest,
    StartNarrativeRequest,
    AdvanceNarrativeRequest,
)
from api.models.responses import (
    WorldResponse,
    NarrativeCommitResponse,
    DramaticStateResponse,
    ChoiceResponse,
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    "CreateWorldRequest",
    "StartNarrativeRequest",
    "AdvanceNarrativeRequest",
    "WorldResponse",
    "NarrativeCommitResponse",
    "DramaticStateResponse",
    "ChoiceResponse",
    "ErrorResponse",
    "HealthResponse",
]
