"""
tests/test_fase2.py — Tests de Fase 2 (Persistencia con PostgreSQL)

Requisitos:
- Docker corriendo con `docker-compose up -d`
- PostgreSQL en localhost:5432
- Migraciones aplicadas: `alembic upgrade head`

Ejecutar:
    pytest tests/test_fase2.py -v
    pytest tests/test_fase2.py -v -m fase2
"""

import pytest
import asyncio
from datetime import datetime

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.models.event import (
    NarrativeEvent, EventType, CausalEdge, EntityDelta,
    WorldVariableDelta, DramaticDelta
)
from cne_core.models.commit import NarrativeCommit, Branch

from persistence.database import DatabaseConfig
from persistence.repositories.postgresql_repository import PostgreSQLRepository


# ── Configuración de pytest ────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Crea un event loop para tests async."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_config():
    """
    Configuración de base de datos para tests.

    IMPORTANTE: Este test requiere PostgreSQL corriendo.
    Levantar con: docker-compose up -d postgres
    """
    config = DatabaseConfig(
        "postgresql+asyncpg://cne_user@localhost:5433/cne_db",
        echo=False  # echo=True para ver las queries SQL
    )

    # Limpiar y crear tablas (en tests reales, usar una DB de test separada)
    await config.drop_all_tables()
    await config.create_all_tables()

    yield config

    # Cleanup
    await config.dispose()


@pytest.fixture
async def repository(db_config):
    """Repository configurado con PostgreSQL."""
    return PostgreSQLRepository(db_config)


@pytest.fixture
def sample_world():
    """WorldDefinition de prueba."""
    hero = Entity(
        name="Aldric",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100, "courage": 80, "alive": True}
    )

    villain = Entity(
        name="Malachar",
        entity_type=EntityType.CHARACTER,
        attributes={"power": 95, "influence": 70, "alive": True}
    )

    return WorldDefinition(
        name="El Reino de las Sombras",
        context="Un reino medieval donde la magia oscura amenaza con destruir todo.",
        protagonist="Aldric, un caballero desterrado que debe redimirse.",
        era="Medieval fantástico, año 843",
        tone=NarrativeTone.DARK,
        antagonist="Malachar el Corrupto",
        rules="La magia oscura tiene un precio: cada hechizo corrompe el alma.",
        constraints=[
            "No hay resurrecciones",
            "La magia tiene consecuencias irreversibles",
        ],
        initial_entities=[hero, villain],
        dramatic_config={
            "tension": 40,
            "hope": 55,
            "chaos": 25,
            "rhythm": 50,
            "saturation": 0,
            "connection": 40,
            "mystery": 60,
        },
        max_depth=50,
    )


# ── Tests ──────────────────────────────────────────────────────────────────────

@pytest.mark.fase2
@pytest.mark.asyncio
async def test_save_and_get_world(repository, sample_world):
    """
    Test básico: guardar y recuperar un WorldDefinition.
    """
    # Guardar
    await repository.save_world(sample_world)

    # Recuperar
    loaded_world = await repository.get_world(sample_world.id)

    # Verificar
    assert loaded_world is not None
    assert loaded_world.id == sample_world.id
    assert loaded_world.name == sample_world.name
    assert loaded_world.tone == sample_world.tone
    assert len(loaded_world.initial_entities) == 2
    assert loaded_world.dramatic_config["tension"] == 40


@pytest.mark.fase2
@pytest.mark.asyncio
async def test_save_commit_and_retrieve_trunk(repository, sample_world):
    """
    Test: guardar commits y recuperar el trunk (cadena de commits).
    """
    await repository.save_world(sample_world)

    # Crear rama
    branch = Branch(
        world_id=sample_world.id,
        origin_commit_id="root",
        name="Test Branch",
    )
    await repository.save_branch(branch)

    # Crear commit inicial
    commit0 = NarrativeCommit(
        world_id=sample_world.id,
        event_id="event_0",
        depth=0,
        narrative_text="El reino está en peligro. Aldric debe decidir...",
        summary="La historia comienza.",
        dramatic_snapshot=sample_world.dramatic_config.copy(),
        branch_id=branch.id,
    )
    await repository.save_commit(commit0)

    # Guardar estado dramático
    await repository.save_dramatic_state(
        commit0.id,
        sample_world.dramatic_config
    )

    # Crear commit hijo
    commit1 = NarrativeCommit(
        world_id=sample_world.id,
        event_id="event_1",
        depth=1,
        parent_id=commit0.id,
        choice_text="Ir al palacio",
        narrative_text="Aldric se dirige al palacio...",
        summary="Aldric acepta la misión.",
        branch_id=commit0.branch_id,
        dramatic_snapshot={
            "tension": 45,
            "hope": 50,
            "chaos": 25,
            "rhythm": 55,
            "saturation": 5,
            "connection": 40,
            "mystery": 58,
        },
    )
    await repository.save_commit(commit1)

    # Recuperar trunk
    trunk = await repository.get_trunk(commit1.id, max_depth=10)

    # Verificar
    assert len(trunk) == 2
    assert trunk[0].id == commit0.id  # Orden cronológico
    assert trunk[1].id == commit1.id
    assert trunk[1].parent_id == commit0.id


@pytest.mark.fase2
@pytest.mark.asyncio
async def test_causal_cycle_detection(repository, sample_world):
    """
    Test: el repository debe detectar ciclos en el grafo causal.

    Intentar crear A→B→A debe fallar.
    """
    await repository.save_world(sample_world)

    # Crear rama
    branch = Branch(
        world_id=sample_world.id,
        origin_commit_id="root",
        name="Test Branch",
    )
    await repository.save_branch(branch)

    # Crear commits y eventos
    commit0 = NarrativeCommit(
        world_id=sample_world.id,
        event_id="event_A",
        depth=0,
        narrative_text="Evento A",
        summary="A",
        branch_id=branch.id,
    )
    await repository.save_commit(commit0)

    event_a = NarrativeEvent(
        commit_id=commit0.id,
        event_type=EventType.DECISION,
        narrative_text="Evento A",
        summary="A",
        depth=0,
    )
    await repository.save_event(event_a)

    commit1 = NarrativeCommit(
        world_id=sample_world.id,
        event_id="event_B",
        depth=1,
        parent_id=commit0.id,
        narrative_text="Evento B",
        summary="B",
        branch_id=branch.id,
    )
    await repository.save_commit(commit1)

    event_b = NarrativeEvent(
        commit_id=commit1.id,
        event_type=EventType.DECISION,
        narrative_text="Evento B",
        summary="B",
        depth=1,
    )
    await repository.save_event(event_b)

    # Crear arista A→B (válida)
    edge_ab = CausalEdge(
        cause_event_id=event_a.id,
        effect_event_id=event_b.id,
    )
    await repository.save_causal_edge(edge_ab)

    # Intentar crear arista B→A (debe fallar por ciclo)
    edge_ba = CausalEdge(
        cause_event_id=event_b.id,
        effect_event_id=event_a.id,
    )

    with pytest.raises(ValueError, match="crearia un ciclo"):
        await repository.save_causal_edge(edge_ba)


@pytest.mark.fase2
@pytest.mark.asyncio
async def test_dramatic_state_persistence(repository, sample_world):
    """
    Test: guardar y recuperar estado dramático.
    """
    await repository.save_world(sample_world)

    # Crear rama
    branch = Branch(
        world_id=sample_world.id,
        origin_commit_id="root",
        name="Test Branch",
    )
    await repository.save_branch(branch)

    commit = NarrativeCommit(
        world_id=sample_world.id,
        event_id="event_test",
        depth=0,
        narrative_text="Test",
        summary="Test",
        branch_id=branch.id,
    )
    await repository.save_commit(commit)

    # Guardar estado dramático
    dramatic_vector = {
        "tension": 75,
        "hope": 30,
        "chaos": 60,
        "rhythm": 80,
        "saturation": 20,
        "connection": 50,
        "mystery": 40,
    }
    await repository.save_dramatic_state(
        commit.id,
        dramatic_vector,
        forced_event="CLIMAX",
        trigger_meter="tension"
    )

    # Recuperar
    loaded_state = await repository.get_dramatic_state(commit.id)

    # Verificar
    assert loaded_state is not None
    assert loaded_state["tension"] == 75
    assert loaded_state["hope"] == 30
    assert loaded_state["chaos"] == 60


@pytest.mark.fase2
@pytest.mark.asyncio
async def test_entity_deltas(repository, sample_world):
    """
    Test: guardar evento con entity deltas y recuperarlo.
    """
    await repository.save_world(sample_world)

    # Crear rama
    branch = Branch(
        world_id=sample_world.id,
        origin_commit_id="root",
        name="Test Branch",
    )
    await repository.save_branch(branch)

    commit = NarrativeCommit(
        world_id=sample_world.id,
        event_id="event_delta",
        depth=0,
        narrative_text="Test deltas",
        summary="Test",
        branch_id=branch.id,
    )
    await repository.save_commit(commit)

    # Crear evento con deltas
    hero = sample_world.initial_entities[0]
    delta = EntityDelta(
        entity_id=hero.id,
        entity_name=hero.name,
        attribute="health",
        old_value=100,
        new_value=85,
    )

    event = NarrativeEvent(
        commit_id=commit.id,
        event_type=EventType.DECISION,
        narrative_text="Aldric es herido en combate.",
        summary="Combate",
        entity_deltas=[delta],
        depth=0,
    )

    await repository.save_event(event)

    # Recuperar evento
    loaded_event = await repository.get_event(event.id)

    # Verificar
    assert loaded_event is not None
    assert len(loaded_event.entity_deltas) == 1
    assert loaded_event.entity_deltas[0].entity_id == hero.id
    assert loaded_event.entity_deltas[0].old_value == 100
    assert loaded_event.entity_deltas[0].new_value == 85


@pytest.mark.fase2
@pytest.mark.asyncio
async def test_list_branches(repository, sample_world):
    """
    Test: crear y listar ramas.
    """
    await repository.save_world(sample_world)

    # Crear rama principal
    branch1 = Branch(
        world_id=sample_world.id,
        origin_commit_id="commit_0",
        name="Rama principal",
        description="El camino del héroe",
    )
    await repository.save_branch(branch1)

    # Crear rama alternativa
    branch2 = Branch(
        world_id=sample_world.id,
        origin_commit_id="commit_0",
        name="Rama oscura",
        description="El camino de la corrupción",
    )
    await repository.save_branch(branch2)

    # Listar ramas
    branches = await repository.list_branches(sample_world.id)

    # Verificar
    assert len(branches) == 2
    assert any(b.name == "Rama principal" for b in branches)
    assert any(b.name == "Rama oscura" for b in branches)


# ── Resumen de tests ───────────────────────────────────────────────────────────

"""
TESTS DE FASE 2:

✅ test_save_and_get_world
   → Persistir WorldDefinition con entidades

✅ test_save_commit_and_retrieve_trunk
   → Cadena de commits con parent_id

✅ test_causal_cycle_detection
   → CTE recursiva detecta ciclos en el DAG

✅ test_dramatic_state_persistence
   → Vector dramático persistido correctamente

✅ test_entity_deltas
   → Deltas de entidades guardados y recuperados

✅ test_list_branches
   → Crear y listar ramas

SIGUIENTE PASO:
- Implementar StateRebuilder completo (reconstrucción desde deltas)
- Tests de performance (queries con N commits grandes)
- Tests de concurrencia (múltiples writers)
"""
