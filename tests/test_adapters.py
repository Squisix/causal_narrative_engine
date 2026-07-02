"""
tests/test_adapters.py - Tests de AI Adapters (MockAdapter + integracion con engine)

Verifica que los adapters generen propuestas validas y que el motor
las procese correctamente. No requiere API keys ni servicios externos.

Ejecutar:
    pytest tests/test_adapters.py -v
"""

import pytest
import asyncio

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.models.event import EntityCreation, DramaticDelta
from cne_core.engine.dramatic_engine import ForcedEventConstraint, ForcedEventType
from cne_core.engine.state_machine import StateMachine
from cne_core.interfaces.ai_adapter import NarrativeContext
from adapters.mock_adapter import MockAdapter


@pytest.fixture
def world_with_entities():
    lyra = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100, "influence": 70},
    )
    malachar = Entity(
        name="Malachar",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 80, "influence": 90},
    )
    castle = Entity(
        name="Castillo Real",
        entity_type=EntityType.LOCATION,
        attributes={"danger_level": 30, "accessible": True},
    )
    return WorldDefinition(
        name="Reino de Eldoria",
        context="Un reino medieval en crisis politica",
        protagonist="Princesa Lyra",
        era="Medieval",
        tone=NarrativeTone.DARK,
        antagonist="Malachar el Corrupto",
        rules="La magia tiene coste vital",
        constraints=["Los muertos no resucitan"],
        initial_entities=[lyra, malachar, castle],
        dramatic_config={
            "tension": 40, "hope": 55, "chaos": 25,
            "rhythm": 50, "saturation": 0, "connection": 40, "mystery": 60,
        },
    )


@pytest.fixture
def mock_adapter():
    return MockAdapter(deterministic=True, seed=42)


def _make_context(world, **kwargs):
    defaults = {
        "world_definition": world,
        "current_depth": 0,
        "current_dramatic_state": world.dramatic_config.copy(),
        "current_entity_states": {
            e.id: {"name": e.name, "type": e.entity_type.value,
                   "attributes": e.attributes.copy(), "alive": True}
            for e in world.initial_entities
        },
        "current_world_vars": {},
        "commit_chain": [],
        "player_choice": None,
        "forced_constraint": None,
    }
    defaults.update(kwargs)
    return NarrativeContext(**defaults)


# -- MockAdapter: generacion basica --

@pytest.mark.asyncio
async def test_basic_generation(world_with_entities, mock_adapter):
    context = _make_context(world_with_entities)
    proposal = await mock_adapter.generate_narrative(context)

    assert proposal is not None
    assert len(proposal.narrative_text) > 50
    assert len(proposal.summary) > 10
    assert len(proposal.choices) >= 2
    assert proposal.dramatic_delta is not None
    assert proposal.causal_reason is not None


@pytest.mark.asyncio
async def test_determinism(world_with_entities):
    adapter1 = MockAdapter(deterministic=True, seed=42)
    adapter2 = MockAdapter(deterministic=True, seed=42)
    context = _make_context(world_with_entities)

    p1 = await adapter1.generate_narrative(context)
    p2 = await adapter2.generate_narrative(context)

    assert p1.narrative_text == p2.narrative_text
    assert p1.summary == p2.summary


@pytest.mark.asyncio
async def test_player_choice_in_proposal(world_with_entities, mock_adapter):
    context = _make_context(
        world_with_entities,
        current_depth=1,
        player_choice="Confrontar a Malachar directamente",
    )
    proposal = await mock_adapter.generate_narrative(context)

    assert proposal is not None
    assert proposal.causal_reason is not None
    text_lower = (proposal.causal_reason + " " + proposal.summary).lower()
    assert "confrontar" in text_lower or "malachar" in text_lower or "decision" in text_lower


# -- MockAdapter: dramatic deltas y choices --

@pytest.mark.asyncio
async def test_dramatic_deltas_in_range(world_with_entities, mock_adapter):
    context = _make_context(world_with_entities)
    proposal = await mock_adapter.generate_narrative(context)

    delta = proposal.dramatic_delta
    for meter in ["tension", "hope", "chaos", "rhythm", "saturation", "connection", "mystery"]:
        value = getattr(delta, meter)
        assert -100 <= value <= 100, f"{meter}={value} fuera de rango"


@pytest.mark.asyncio
async def test_choices_have_previews(world_with_entities, mock_adapter):
    context = _make_context(world_with_entities)
    proposal = await mock_adapter.generate_narrative(context)

    assert 2 <= len(proposal.choices) <= 5
    for choice in proposal.choices:
        assert len(choice.text) > 5
        assert choice.dramatic_preview is not None
        assert "tension" in choice.dramatic_preview
        assert "hope" in choice.dramatic_preview


# -- MockAdapter: forced events --

@pytest.mark.asyncio
async def test_forced_event_constraint(world_with_entities, mock_adapter):
    forced = ForcedEventConstraint(
        event_type=ForcedEventType.CLIMAX,
        description="La tension ha alcanzado su punto maximo. Debe ocurrir un climax.",
        trigger_meter="tension",
        trigger_value=90,
    )
    context = _make_context(
        world_with_entities,
        current_depth=5,
        current_dramatic_state={"tension": 90, "hope": 30, "chaos": 60,
                                "rhythm": 50, "saturation": 70,
                                "connection": 40, "mystery": 65},
        forced_constraint=forced,
    )
    proposal = await mock_adapter.generate_narrative(context)

    assert proposal is not None
    assert "CLIMAX" in proposal.narrative_text or "critico" in proposal.narrative_text.lower()


# -- MockAdapter: stats y error mode --

@pytest.mark.asyncio
async def test_stats_tracking(world_with_entities, mock_adapter):
    context = _make_context(world_with_entities)
    for _ in range(5):
        await mock_adapter.generate_narrative(context)

    stats = mock_adapter.get_stats()
    assert stats["total_calls"] == 5
    assert stats["deterministic"] is True


@pytest.mark.asyncio
async def test_error_mode(world_with_entities):
    error_adapter = MockAdapter(deterministic=True, force_errors=True)
    context = _make_context(world_with_entities)
    proposal = await error_adapter.generate_narrative(context)

    assert proposal is not None
    assert len(proposal.narrative_text) < 50


# -- Integracion: MockAdapter + StateMachine --

@pytest.mark.asyncio
async def test_full_engine_flow_with_mock(world_with_entities, mock_adapter):
    """Flujo completo: mock genera -> engine procesa -> estado coherente."""
    engine = StateMachine(world=world_with_entities)
    context = _make_context(world_with_entities)

    # Start
    proposal = await mock_adapter.generate_narrative(context)
    result = engine.start(
        initial_narrative=proposal.narrative_text,
        initial_choices=proposal.choices,
        initial_summary=proposal.summary,
        initial_dramatic_delta=proposal.dramatic_delta,
        causal_reason=proposal.causal_reason,
    )

    assert result.commit.depth == 0
    assert result.event is not None
    assert result.event.causal_reason == proposal.causal_reason

    # Advance
    choice = result.available_choices[0].text
    context2 = _make_context(
        world_with_entities,
        current_depth=1,
        current_dramatic_state=result.dramatic_state,
        player_choice=choice,
    )
    proposal2 = await mock_adapter.generate_narrative(context2)
    result2 = engine.advance_story(
        choice_text=choice,
        narrative_text=proposal2.narrative_text,
        summary=proposal2.summary,
        choices=proposal2.choices,
        entity_deltas=proposal2.entity_deltas or None,
        world_deltas=proposal2.world_deltas or None,
        dramatic_delta=proposal2.dramatic_delta,
        causal_reason=proposal2.causal_reason,
    )

    assert result2.commit.depth == 1
    assert result2.commit.parent_id == result.commit.id
    assert result2.event is not None
    assert result2.event.causal_reason == proposal2.causal_reason
    assert len(result2.causal_edges) == 1
    assert result2.causal_edges[0].cause_event_id == result.event.id
    assert result2.causal_edges[0].effect_event_id == result2.event.id


@pytest.mark.asyncio
async def test_entity_creation_in_advance(world_with_entities):
    """Verifica que entity_creations se aplican correctamente al avanzar la historia."""
    engine = StateMachine(world=world_with_entities)

    from cne_core.models.commit import NarrativeChoice
    result0 = engine.start(
        initial_narrative="La historia comienza en el reino. " * 5,
        initial_choices=[NarrativeChoice(text="Explorar"), NarrativeChoice(text="Esperar")],
        initial_summary="Inicio de la historia.",
        causal_reason="Evento inicial del mundo.",
    )

    initial_entity_count = len(engine._entities)

    # Avanzar con entity_creations (un nuevo personaje + un artifact)
    creations = [
        EntityCreation(
            entity_name="Zara la Errante",
            entity_type="character",
            attributes={"health": 100, "loyalty": 50},
        ),
        EntityCreation(
            entity_name="Llave del Santuario",
            entity_type="artifact",
            attributes={"possessed_by": None, "location": "altar", "usable": True, "effect": "Abre el santuario"},
        ),
    ]

    result1 = engine.advance_story(
        choice_text="Explorar",
        narrative_text="Mientras explora, Lyra encuentra a una extranjera y una llave misteriosa. " * 3,
        summary="Lyra encuentra a Zara y una llave misteriosa.",
        choices=[NarrativeChoice(text="Hablar con Zara"), NarrativeChoice(text="Tomar la llave")],
        entity_creations=creations,
        dramatic_delta=DramaticDelta(mystery=10, connection=5),
        causal_reason="La exploracion revela nuevos elementos.",
    )

    # Debe haber 2 entidades mas
    assert len(engine._entities) == initial_entity_count + 2

    # Verificar que las entidades existen con los atributos correctos
    zara = None
    llave = None
    for eid, entity in engine._entities.items():
        if entity.name == "Zara la Errante":
            zara = entity
        elif entity.name == "Llave del Santuario":
            llave = entity

    assert zara is not None, "Zara no fue creada"
    assert zara.entity_type == EntityType.CHARACTER
    assert zara.attributes["health"] == 100
    assert zara.attributes["created_at_depth"] == 1

    assert llave is not None, "Llave no fue creada"
    assert llave.entity_type == EntityType.ARTIFACT
    assert llave.attributes["possessed_by"] is None
    assert llave.attributes["usable"] is True

    # El evento debe registrar las entity_creations
    assert len(result1.event.entity_creations) == 2

    # El snapshot del commit debe incluir las nuevas entidades
    assert zara.id in result1.commit.entity_states
    assert llave.id in result1.commit.entity_states


@pytest.mark.asyncio
async def test_entity_creation_not_in_previous_commit(world_with_entities):
    """go_to_commit a un commit anterior NO debe incluir entidades creadas despues."""
    engine = StateMachine(world=world_with_entities)

    from cne_core.models.commit import NarrativeChoice
    result0 = engine.start(
        initial_narrative="La historia comienza en el reino. " * 5,
        initial_choices=[NarrativeChoice(text="Explorar"), NarrativeChoice(text="Esperar")],
        initial_summary="Inicio.",
        causal_reason="Evento inicial.",
    )
    commit0_id = result0.commit.id
    initial_entity_count = len(engine._entities)

    # Avanzar con una entity_creation
    result1 = engine.advance_story(
        choice_text="Explorar",
        narrative_text="Un nuevo personaje aparece en la historia de forma inesperada. " * 3,
        summary="Aparece un extranjero.",
        choices=[NarrativeChoice(text="Saludar"), NarrativeChoice(text="Huir")],
        entity_creations=[
            EntityCreation(entity_name="Extranjero", entity_type="character", attributes={"health": 80}),
        ],
        causal_reason="Un extranjero llega al reino.",
    )

    assert len(engine._entities) == initial_entity_count + 1

    # go_to_commit al commit 0 debe restaurar sin el extranjero
    engine.go_to_commit(commit0_id)
    assert len(engine._entities) == initial_entity_count


def test_response_schema_entity_creations():
    """Verifica que NarrativeResponse parsea entity_creations y retorna 5-tuple."""
    from cne_core.ai.response_schema import NarrativeResponse

    data = {
        "narrative": "Un evento narrativo inmersivo donde aparece un objeto magico que cambia todo. " * 3,
        "summary": "Un objeto magico aparece.",
        "choices": ["Tomar el objeto", "Ignorar el objeto"],
        "entity_creations": [
            {"entity_name": "Espada Flamigera", "entity_type": "artifact",
             "attributes": {"possessed_by": None, "location": "cueva", "usable": True, "effect": "Quema enemigos"}},
        ],
        "dramatic_deltas": {"tension": 5, "hope": 0, "chaos": 0, "rhythm": 0,
                            "saturation": 0, "connection": 0, "mystery": 10},
        "causal_reason": "El personaje descubre un arma antigua en la cueva.",
    }

    response = NarrativeResponse(**data)
    assert len(response.entity_creations) == 1
    assert response.entity_creations[0].entity_name == "Espada Flamigera"
    assert response.entity_creations[0].entity_type == "artifact"

    entity_deltas, entity_creations, world_deltas, dramatic_delta, choices = response.to_core_models()
    assert len(entity_creations) == 1
    assert entity_creations[0].entity_name == "Espada Flamigera"
    assert entity_creations[0].attributes["effect"] == "Quema enemigos"


@pytest.mark.asyncio
async def test_entity_states_in_context(world_with_entities):
    """Verifica que entity_states se pasa correctamente al contexto."""
    entity_states = {
        "id-1": {"name": "Lyra", "type": "character",
                 "attributes": {"health": 75, "influence": 80}, "alive": True},
        "id-2": {"name": "Malachar", "type": "character",
                 "attributes": {"health": 80, "influence": 90}, "alive": True},
    }

    context = _make_context(
        world_with_entities,
        current_entity_states=entity_states,
    )

    assert context.current_entity_states == entity_states
    assert context.current_entity_states["id-1"]["attributes"]["health"] == 75
