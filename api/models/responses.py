"""
api/models/responses.py - Response schemas

Schemas de Pydantic para responses de la API.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DramaticStateResponse(BaseModel):
    """Estado del vector dramático."""
    tension: int = Field(..., ge=0, le=100)
    hope: int = Field(..., ge=0, le=100)
    chaos: int = Field(..., ge=0, le=100)
    rhythm: int = Field(..., ge=0, le=100)
    saturation: int = Field(..., ge=0, le=100)
    connection: int = Field(..., ge=0, le=100)
    mystery: int = Field(..., ge=0, le=100)


class ChoiceResponse(BaseModel):
    """Una opción disponible para el jugador."""
    text: str
    dramatic_preview: Optional[dict[str, int]] = None
    tone_hint: Optional[str] = None


class NarrativeCommitResponse(BaseModel):
    """
    Respuesta con el estado de un commit narrativo.

    Incluye la narrativa generada, opciones, y estado del mundo.
    """
    commit_id: str
    depth: int

    # Narrativa
    narrative_text: str
    summary: str
    choices: list[ChoiceResponse]

    # Estado dramático
    dramatic_state: DramaticStateResponse

    # Metadata
    causal_reason: Optional[str] = None
    is_ending: bool = False
    forced_event_type: Optional[str] = None

    # Timestamps
    created_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "commit_id": "a1b2c3d4-...",
                "depth": 1,
                "narrative_text": "La sala del trono está en silencio cuando Lyra recibe la noticia...",
                "summary": "El rey Aldric muere misteriosamente. Lyra asume el trono.",
                "choices": [
                    {
                        "text": "Confrontar a Malachar directamente",
                        "dramatic_preview": {"tension": 15, "hope": -5, "chaos": 5},
                        "tone_hint": "confrontacional"
                    },
                    {
                        "text": "Ordenar una investigación secreta",
                        "dramatic_preview": {"tension": 5, "hope": 5, "chaos": 0},
                        "tone_hint": "cauteloso"
                    }
                ],
                "dramatic_state": {
                    "tension": 35,
                    "hope": 55,
                    "chaos": 22,
                    "rhythm": 50,
                    "saturation": 3,
                    "connection": 45,
                    "mystery": 60
                },
                "causal_reason": "Este es el evento inicial que establece el conflicto",
                "is_ending": False,
                "forced_event_type": None,
                "created_at": "2026-03-23T19:30:00Z"
            }
        }


class WorldResponse(BaseModel):
    """
    Respuesta con información de un mundo.
    """
    world_id: str
    name: str
    context: str
    protagonist: str
    era: str
    tone: str
    antagonist: str
    rules: str
    constraints: list[str]
    max_depth: int

    # Estado
    created_at: datetime
    total_commits: int = 0
    active_branches: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "world_id": "w1x2y3z4-...",
                "name": "Reino de Valdris",
                "context": "Un reino medieval al borde de la guerra...",
                "protagonist": "Lyra, la princesa heredera",
                "era": "Medieval fantástico, año 843",
                "tone": "dark",
                "antagonist": "Malachar, el consejero corrupto",
                "rules": "La magia existe pero tiene un precio",
                "constraints": ["No viajes en el tiempo"],
                "max_depth": 20,
                "created_at": "2026-03-23T19:00:00Z",
                "total_commits": 5,
                "active_branches": 2
            }
        }


class ErrorResponse(BaseModel):
    """
    Respuesta de error estándar.
    """
    error: str
    detail: Optional[str] = None
    error_code: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "error": "World not found",
                "detail": "No world exists with ID: xyz123",
                "error_code": "WORLD_NOT_FOUND"
            }
        }


class HealthResponse(BaseModel):
    """
    Respuesta del health check.
    """
    status: str = "ok"
    version: str
    timestamp: datetime

    # Servicios
    database: str = "unknown"
    ai_adapter: str = "unknown"

    class Config:
        json_schema_extra = {
            "example": {
                "status": "ok",
                "version": "0.3.0",
                "timestamp": "2026-03-23T19:00:00Z",
                "database": "connected",
                "ai_adapter": "mock"
            }
        }


class StatsResponse(BaseModel):
    """
    Estadísticas del motor.
    """
    total_worlds: int
    total_commits: int
    total_events: int
    ai_adapter_stats: Optional[dict] = None

    class Config:
        json_schema_extra = {
            "example": {
                "total_worlds": 10,
                "total_commits": 150,
                "total_events": 200,
                "ai_adapter_stats": {
                    "total_calls": 50,
                    "total_tokens_used": 125000,
                    "avg_tokens_per_call": 2500
                }
            }
        }
