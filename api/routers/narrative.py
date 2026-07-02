"""
api/routers/narrative.py - Narrative flow endpoints

Endpoints para generar narrativa y avanzar la historia.
"""

from fastapi import APIRouter, HTTPException, Depends

from api.models.requests import StartNarrativeRequest, AdvanceNarrativeRequest
from api.models.responses import NarrativeCommitResponse, DramaticStateResponse, ChoiceResponse, CommitSummaryResponse, ExistingPathResponse
from api.services.narrative_service_v2 import NarrativeServiceV2
from api.dependencies import get_narrative_service_v2, get_ai_adapter

router = APIRouter(
    prefix="",
    tags=["narrative"]
)


@router.post("/worlds/{world_id}/start", response_model=NarrativeCommitResponse, status_code=201)
async def start_narrative(
    world_id: str,
    request: StartNarrativeRequest,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Inicia una nueva narrativa en un mundo.

    Genera el primer commit con la IA y retorna las opciones iniciales.
    """
    try:
        # Verificar que el mundo existe
        world = await service.get_world(world_id)
        if not world:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        # Obtener AI adapter
        adapter = get_ai_adapter(
            adapter_type=request.adapter_type,
            adapter_config=request.adapter_config or {}
        )

        # Iniciar narrativa
        commit = await service.start_narrative(
            world_id=world_id,
            adapter=adapter
        )

        # Convertir a response
        return await _commit_to_response(commit, service)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/commits/{commit_id}/advance", response_model=NarrativeCommitResponse, status_code=201)
async def advance_narrative(
    commit_id: str,
    request: AdvanceNarrativeRequest,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Avanza la narrativa tomando una decisión.

    Genera el siguiente commit basado en la elección del jugador.
    """
    try:
        # Verificar que el commit existe
        commit = await service.get_commit(commit_id)
        if not commit:
            raise HTTPException(status_code=404, detail=f"Commit not found: {commit_id}")

        adapter = get_ai_adapter(
            adapter_type=request.adapter_type,
            adapter_config=request.adapter_config or {}
        )

        # Avanzar narrativa
        new_commit = await service.advance_narrative(
            commit_id=commit_id,
            choice=request.choice,
            adapter=adapter,
            custom_choice=request.custom,
        )

        # Convertir a response
        return await _commit_to_response(new_commit, service)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/worlds/{world_id}/commits", response_model=list[CommitSummaryResponse])
async def list_commits(
    world_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """Lista todos los commits de un mundo (resumen ligero)."""
    commits = await service.repo.list_commits(world_id)
    return [
        CommitSummaryResponse(
            commit_id=c.id,
            depth=c.depth,
            summary=c.summary,
            choice_text=c.choice_text,
            is_ending=c.is_ending,
            created_at=c.created_at,
        )
        for c in commits
    ]


@router.get("/worlds/{world_id}/latest", response_model=NarrativeCommitResponse)
async def get_latest_commit(
    world_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """Obtiene el ultimo commit de un mundo (para continuar una historia)."""
    latest_id = await service.repo.get_latest_commit_id(world_id)
    if not latest_id:
        raise HTTPException(status_code=404, detail=f"No commits found for world: {world_id}")

    commit = await service.get_commit(latest_id)
    if not commit:
        raise HTTPException(status_code=404, detail=f"Commit not found: {latest_id}")

    return await _commit_to_response(commit, service)


@router.post("/commits/{commit_id}/goto", response_model=NarrativeCommitResponse)
async def goto_commit(
    commit_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """Navega a un commit específico, restaurando el estado del engine."""
    try:
        commit = await service.goto_commit(commit_id)
        return await _commit_to_response(commit, service)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/commits/{commit_id}", response_model=NarrativeCommitResponse)
async def get_commit(
    commit_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Obtiene información de un commit específico.
    """
    commit = await service.get_commit(commit_id)

    if not commit:
        raise HTTPException(status_code=404, detail=f"Commit not found: {commit_id}")

    return await _commit_to_response(commit, service)


@router.get("/commits/{commit_id}/dramatic", response_model=DramaticStateResponse)
async def get_dramatic_state(
    commit_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Obtiene el estado dramático de un commit.
    """
    commit = await service.get_commit(commit_id)

    if not commit:
        raise HTTPException(status_code=404, detail=f"Commit not found: {commit_id}")

    # Obtener dramatic state del commit (guardado como dramatic_snapshot)
    dramatic_snapshot = commit.dramatic_snapshot or {}

    return DramaticStateResponse(
        tension=dramatic_snapshot.get("tension", 30),
        hope=dramatic_snapshot.get("hope", 60),
        chaos=dramatic_snapshot.get("chaos", 20),
        rhythm=dramatic_snapshot.get("rhythm", 50),
        saturation=dramatic_snapshot.get("saturation", 0),
        connection=dramatic_snapshot.get("connection", 40),
        mystery=dramatic_snapshot.get("mystery", 50),
    )


async def _commit_to_response(commit, service: NarrativeServiceV2) -> NarrativeCommitResponse:
    """Helper para convertir NarrativeCommit a NarrativeCommitResponse."""
    commit_choices = await service.get_commit_choices(commit.id)

    # Convertir choices
    choices = [
        ChoiceResponse(
            text=choice.text,
            dramatic_preview=choice.dramatic_preview,
            tone_hint=choice.tone_hint,
        )
        for choice in commit_choices
    ]

    # Dramatic state (el commit lo guarda como dramatic_snapshot)
    dramatic_snapshot = commit.dramatic_snapshot or {}
    dramatic_state = DramaticStateResponse(
        tension=dramatic_snapshot.get("tension", 30),
        hope=dramatic_snapshot.get("hope", 60),
        chaos=dramatic_snapshot.get("chaos", 20),
        rhythm=dramatic_snapshot.get("rhythm", 50),
        saturation=dramatic_snapshot.get("saturation", 0),
        connection=dramatic_snapshot.get("connection", 40),
        mystery=dramatic_snapshot.get("mystery", 50),
    )

    # Forced event type (si existe)
    forced_event_type = await service.get_forced_event_type(commit.id)

    # Caminos ya explorados (hijos existentes)
    children = await service.repo.get_children_commits(commit.id)
    existing_paths = [
        ExistingPathResponse(
            commit_id=child.id,
            choice_text=child.choice_text or "",
            depth=child.depth,
            summary=child.summary,
        )
        for child in children
        if child.choice_text
    ]

    # Causal reason (from persisted event if available)
    causal_reason = None
    events = await service.repo.get_events_for_commit(commit.id)
    if events:
        causal_reason = events[0].causal_reason

    return NarrativeCommitResponse(
        commit_id=commit.id,
        parent_id=commit.parent_id,
        depth=commit.depth,
        narrative_text=commit.narrative_text,
        summary=commit.summary,
        choices=choices,
        existing_paths=existing_paths,
        dramatic_state=dramatic_state,
        causal_reason=causal_reason,
        is_ending=commit.is_ending,
        forced_event_type=forced_event_type,
        created_at=commit.created_at,
    )
