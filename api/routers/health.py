"""
api/routers/health.py - Health check endpoints

Endpoints para verificar el estado de la API.
"""

from fastapi import APIRouter, Depends
from datetime import datetime

from api.models.responses import HealthResponse, StatsResponse
from api.config import Settings, get_settings
from api.services.narrative_service_v2 import NarrativeServiceV2
from api.dependencies import get_narrative_service_v2

router = APIRouter(
    prefix="",
    tags=["health"]
)


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: Settings = Depends(get_settings)):
    """
    Health check endpoint.

    Verifica que la API esté funcionando.
    """
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(),
        database="not_implemented",  # Fase 2
        ai_adapter=settings.default_ai_adapter,
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats(
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Estadísticas del motor desde PostgreSQL.
    """
    stats = await service.get_global_stats()

    return StatsResponse(
        total_worlds=stats["total_worlds"],
        total_commits=stats["total_commits"],
        total_events=stats["total_events"],
        ai_adapter_stats=None,
    )
