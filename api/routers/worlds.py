"""
api/routers/worlds.py - World management endpoints

Endpoints to create and manage worlds (seeds).
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from api.models.requests import CreateWorldRequest
from api.models.responses import WorldResponse, ErrorResponse
from api.services.narrative_service_v2 import NarrativeServiceV2
from api.dependencies import get_narrative_service_v2
from cne_core.models.world import WorldDefinition, NarrativeTone, Entity, EntityType

router = APIRouter(
    prefix="/worlds",
    tags=["worlds"]
)


@router.get("", response_model=list[WorldResponse])
async def list_worlds(
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """Lists all created worlds."""
    try:
        worlds = await service.repo.list_worlds()
        results = []
        for world in worlds:
            stats = await service.get_world_stats(world.id)
            results.append(WorldResponse(
                world_id=world.id,
                name=world.name,
                context=world.context,
                protagonist=world.protagonist,
                era=world.era,
                tone=world.tone.value,
                antagonist=world.antagonist,
                rules=world.rules,
                constraints=world.constraints,
                max_depth=world.max_depth,
                output_language=world.output_language,
                created_at=world.created_at,
                total_commits=stats["total_commits"],
                active_branches=stats["active_branches"],
            ))
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=WorldResponse, status_code=201)
async def create_world(
    request: CreateWorldRequest,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Creates a new world (seed) to start stories.

    The world defines the rules, tone, protagonist, and initial dramatic vector settings.
    """
    try:
        # Validate tone directly from the English enum
        try:
            tone_enum = NarrativeTone(request.tone.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tone: {request.tone}. Valid values: epic, dark, mysterious, adventurous, philosophical, black_humor"
            )

        # Convert initial entities
        entities = []
        for er in request.initial_entities:
            try:
                etype = EntityType(er.entity_type)
            except ValueError:
                etype = EntityType.CHARACTER
            entities.append(Entity(
                name=er.name,
                entity_type=etype,
                attributes=er.attributes,
            ))

        # Create WorldDefinition
        world = WorldDefinition(
            name=request.name,
            context=request.context,
            protagonist=request.protagonist,
            era=request.era,
            tone=tone_enum,
            antagonist=request.antagonist or "unknown",
            rules=request.rules or "The world follows its own laws",
            constraints=request.constraints or [],
            initial_entities=entities,
            dramatic_config=request.dramatic_config or {
                "tension": 30,
                "hope": 60,
                "chaos": 20,
                "rhythm": 50,
                "saturation": 0,
                "connection": 40,
                "mystery": 50,
            },
            max_depth=request.max_depth,
            output_language=request.output_language or "es",
        )

        # Save in PostgreSQL
        await service.save_world(world)

        return WorldResponse(
            world_id=world.id,
            name=world.name,
            context=world.context,
            protagonist=world.protagonist,
            era=world.era,
            tone=world.tone.value,
            antagonist=world.antagonist,
            rules=world.rules,
            constraints=world.constraints,
            max_depth=world.max_depth,
            output_language=world.output_language,
            created_at=world.created_at,
            total_commits=0,
            active_branches=0,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{world_id}", response_model=WorldResponse)
async def get_world(
    world_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Retrieves world information by its ID.
    """
    try:
        print(f"[GET /worlds/{world_id}] Starting...")
        world = await service.get_world(world_id)
        print(f"[GET /worlds/{world_id}] Got world: {world.name if world else None}")

        if not world:
            raise HTTPException(
                status_code=404,
                detail=f"World not found: {world_id}"
            )

        # Stats from PostgreSQL
        stats = await service.get_world_stats(world_id)
        total_commits = stats["total_commits"]
        active_branches = stats["active_branches"]

        return WorldResponse(
            world_id=world.id,
            name=world.name,
            context=world.context,
            protagonist=world.protagonist,
            era=world.era,
            tone=world.tone.value,
            antagonist=world.antagonist,
            rules=world.rules,
            constraints=world.constraints,
            max_depth=world.max_depth,
            output_language=world.output_language,
            created_at=world.created_at,
            total_commits=total_commits,
            active_branches=active_branches,
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving world: {str(e)}")


@router.delete("/{world_id}", status_code=204)
async def delete_world(
    world_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Deletes a world and all its associated stories.

    ⚠️ This operation is irreversible.
    """
    deleted = await service.delete_world(world_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"World not found: {world_id}"
        )

    return None  # 204 No Content
