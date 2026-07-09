"""
api/models/responses.py - Response schemas

Pydantic schemas for API responses.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class DramaticStateResponse(BaseModel):
    """Dramatic vector state response."""
    tension: int = Field(..., ge=0, le=100)
    hope: int = Field(..., ge=0, le=100)
    chaos: int = Field(..., ge=0, le=100)
    rhythm: int = Field(..., ge=0, le=100)
    saturation: int = Field(..., ge=0, le=100)
    connection: int = Field(..., ge=0, le=100)
    mystery: int = Field(..., ge=0, le=100)


class ChoiceResponse(BaseModel):
    """An available choice for the player."""
    text: str
    tone_hint: Optional[str] = None


class ExistingPathResponse(BaseModel):
    """An already explored path (existing child of this commit)."""
    commit_id: str
    choice_text: str
    depth: int
    summary: str


class NarrativeCommitResponse(BaseModel):
    """
    Response containing the state of a narrative commit.

    Includes the generated narrative, options, and world state.
    """
    commit_id: str
    parent_id: Optional[str] = None
    depth: int

    # Narrative
    narrative_text: str
    summary: str
    choices: list[ChoiceResponse]
    existing_paths: list[ExistingPathResponse] = []

    # Dramatic state
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
                "narrative_text": "The throne room is dead silent as Lyra receives the news...",
                "summary": "King Aldric dies mysteriously. Lyra assumes the throne.",
                "choices": [
                    {
                        "text": "Confront Malachar directly",
                        "tone_hint": "confrontational"
                    },
                    {
                        "text": "Order a secret investigation",
                        "tone_hint": "cautious"
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
                "causal_reason": "This is the initial event setting up the conflict",
                "is_ending": False,
                "forced_event_type": None,
                "created_at": "2026-03-23T19:30:00Z"
            }
        }


class CommitSummaryResponse(BaseModel):
    """Lightweight summary of a commit for list views."""
    commit_id: str
    depth: int
    summary: str
    choice_text: Optional[str] = None
    is_ending: bool = False
    created_at: datetime


class WorldResponse(BaseModel):
    """
    Response with world information.
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
    output_language: str = "es"

    # State
    created_at: datetime
    total_commits: int = 0
    active_branches: int = 0

    class Config:
        json_schema_extra = {
            "example": {
                "world_id": "w1x2y3z4-...",
                "name": "Kingdom of Valdris",
                "context": "A medieval kingdom on the brink of war...",
                "protagonist": "Lyra, the crown princess",
                "era": "Medieval fantasy, year 843",
                "tone": "dark",
                "antagonist": "Malachar, the corrupt counselor",
                "rules": "Magic exists but has a price",
                "constraints": ["No time travel allowed"],
                "max_depth": 20,
                "output_language": "es",
                "created_at": "2026-03-23T19:00:00Z",
                "total_commits": 5,
                "active_branches": 2
            }
        }


class ErrorResponse(BaseModel):
    """
    Standard error response.
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
    Health check response.
    """
    status: str = "ok"
    version: str
    timestamp: datetime

    # Services
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
    Engine statistics.
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
