"""
api/routers/narrative.py - Narrative flow endpoints

Endpoints to generate narrative and advance the story.
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
    Starts a new narrative in a world.

    Generates the first commit with AI and returns the initial choices.
    """
    try:
        # Verify that the world exists
        world = await service.get_world(world_id)
        if not world:
            raise HTTPException(status_code=404, detail=f"World not found: {world_id}")

        # Get AI adapter
        adapter = get_ai_adapter(
            adapter_type=request.adapter_type,
            adapter_config=request.adapter_config or {}
        )

        # Start narrative
        commit = await service.start_narrative(
            world_id=world_id,
            adapter=adapter
        )

        # Convert to response
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
    Advances the narrative by making a decision.

    Generates the next commit based on the player's choice.
    """
    try:
        # Verify that the commit exists
        commit = await service.get_commit(commit_id)
        if not commit:
            raise HTTPException(status_code=404, detail=f"Commit not found: {commit_id}")

        adapter = get_ai_adapter(
            adapter_type=request.adapter_type,
            adapter_config=request.adapter_config or {}
        )

        # Advance narrative
        new_commit = await service.advance_narrative(
            commit_id=commit_id,
            choice=request.choice,
            adapter=adapter,
            custom_choice=request.custom,
        )

        # Convert to response
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
    """Lists all commits of a world (lightweight summary)."""
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
    """Gets the latest commit of a world (to continue a story)."""
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
    """Navigates to a specific commit, restoring the engine state."""
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
    Gets information about a specific commit.
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
    Gets the dramatic state of a commit.
    """
    commit = await service.get_commit(commit_id)

    if not commit:
        raise HTTPException(status_code=404, detail=f"Commit not found: {commit_id}")

    # Get dramatic state from the commit (stored as dramatic_snapshot)
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
    """Helper to convert NarrativeCommit to NarrativeCommitResponse."""
    commit_choices = await service.get_commit_choices(commit.id)

    # Convert choices
    choices = [
        ChoiceResponse(
            text=choice.text,
            dramatic_preview=choice.dramatic_preview,
            tone_hint=choice.tone_hint,
        )
        for choice in commit_choices
    ]

    # Dramatic state (the commit stores it as dramatic_snapshot)
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

    # Forced event type (if it exists)
    forced_event_type = await service.get_forced_event_type(commit.id)

    # Already explored paths (existing children)
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
