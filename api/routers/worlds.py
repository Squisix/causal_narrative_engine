"""
api/routers/worlds.py - World management endpoints

Endpoints para crear y gestionar mundos (semillas).
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
    """Lista todos los mundos creados."""
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
    Crea un nuevo mundo (semilla) para iniciar historias.

    El mundo define las reglas, tono, protagonista, y configuración dramática inicial.
    """
    try:
        # Validar tone
        # Mapeo de valores en inglés a los valores del enum (español)
        tone_map = {
            "epic": "épico",
            "dark": "oscuro",
            "mysterious": "misterioso",
            "adventurous": "aventurero",
            "philosophical": "filosófico",
            "black_humor": "humor_negro",
        }

        tone_value = tone_map.get(request.tone.lower(), request.tone.lower())

        try:
            tone_enum = NarrativeTone(tone_value)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid tone: {request.tone}. Valid values: epic, dark, mysterious, adventurous, philosophical, black_humor"
            )

        # Convertir entidades iniciales
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

        # Crear WorldDefinition
        world = WorldDefinition(
            name=request.name,
            context=request.context,
            protagonist=request.protagonist,
            era=request.era,
            tone=tone_enum,
            antagonist=request.antagonist or "desconocido",
            rules=request.rules or "El mundo sigue sus propias leyes",
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
        )

        # Guardar en PostgreSQL
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
            created_at=world.created_at,
            total_commits=0,
            active_branches=0,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{world_id}", response_model=WorldResponse)
async def get_world(
    world_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Obtiene información de un mundo por su ID.
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

        # Stats desde PostgreSQL
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
            created_at=world.created_at,
            total_commits=total_commits,
            active_branches=active_branches,
        )
    except HTTPException:
        raise
    except Exception as e:
        # Log the actual error
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error retrieving world: {str(e)}")


@router.delete("/{world_id}", status_code=204)
async def delete_world(
    world_id: str,
    service: NarrativeServiceV2 = Depends(get_narrative_service_v2)
):
    """
    Elimina un mundo y todas sus historias asociadas.

    ⚠️ Esta operación es irreversible.
    """
    deleted = await service.delete_world(world_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"World not found: {world_id}"
        )

    return None  # 204 No Content
