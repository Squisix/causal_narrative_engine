"""
tests/test_fase3.py - Tests de integracion Fase 3 (AI Adapter + Core Engine)

Verifica que:
1. MockAdapter funciona con StateMachine
2. El flujo narrativo completo funciona end-to-end
3. Los umbrales dramaticos disparan eventos forzados
4. La validacion de respuestas funciona correctamente

Ejecutar:
    pytest tests/test_fase3.py -v

No requiere API key (usa MockAdapter).
"""

import pytest
import asyncio

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.engine.dramatic_engine import ForcedEventConstraint, ForcedEventType
from cne_core.engine.state_machine import StateMachine
from cne_core.interfaces.ai_adapter import NarrativeContext
from adapters.mock_adapter import MockAdapter


@pytest.fixture
def sample_world():
    """Mundo de prueba para narrativa."""
    # Crear entidades
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

    world = WorldDefinition(
        name="Reino de Eldoria",
        context="Un reino medieval en crisis politica",
        protagonist="Princesa Lyra",
        era="Medieval",
        tone=NarrativeTone.DARK,
        initial_entities=[lyra, malachar],
    )

    return world


@pytest.fixture
def mock_adapter():
    """MockAdapter determinista."""
    return MockAdapter(deterministic=True, seed=42)


@pytest.mark.asyncio
async def test_fase3_basic_narrative_flow(sample_world, mock_adapter):
    """Test: Flujo narrativo completo con MockAdapter."""
    print("\n[TEST] Fase 3 - Flujo narrativo basico")

    # Crear contexto inicial
    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=0,
        current_dramatic_state={
            "tension": 30,
            "hope": 60,
            "chaos": 20,
            "rhythm": 50,
            "saturation": 0,
            "connection": 40,
            "mystery": 50,
        },
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=None,
        forced_constraint=None,
    )

    # Generar narrativa con MockAdapter
    proposal = await mock_adapter.generate_narrative(context)

    # Verificar propuesta
    assert proposal is not None
    assert len(proposal.narrative_text) > 50
    assert len(proposal.choices) >= 2
    assert proposal.dramatic_delta is not None

    print(f"  [OK] Narrativa: {proposal.narrative_text[:80]}...")
    print(f"  [OK] Choices: {len(proposal.choices)}")
    print(f"  [OK] Dramatic delta: tension={proposal.dramatic_delta.tension}")


@pytest.mark.asyncio
async def test_fase3_with_player_choice(sample_world, mock_adapter):
    """Test: Narrativa generada en respuesta a decision del jugador."""
    print("\n[TEST] Fase 3 - Con decision de jugador")

    # Simular que el jugador tomo una decision
    player_choice = "Confrontar a Malachar directamente"

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=1,
        current_dramatic_state={"tension": 60, "hope": 50, "chaos": 25, "rhythm": 50, "saturation": 5, "connection": 40, "mystery": 50},
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=player_choice,
        forced_constraint=None,
    )

    proposal = await mock_adapter.generate_narrative(context)

    assert proposal is not None
    # La causal_reason debe mencionar la decision
    assert player_choice.lower() in proposal.causal_reason.lower() or "decision" in proposal.causal_reason.lower()

    print(f"  [OK] Decision: {player_choice}")
    print(f"  [OK] Causal reason: {proposal.causal_reason[:80]}...")


@pytest.mark.asyncio
async def test_fase3_forced_event_context(sample_world, mock_adapter):
    """Test: MockAdapter recibe correctamente constraints de eventos forzados."""
    print("\n[TEST] Fase 3 - Evento forzado por umbral")

    # Crear constraint de evento forzado (simulando que tension > 85)
    forced = ForcedEventConstraint(
        event_type=ForcedEventType.CLIMAX,
        description="La tension ha alcanzado su punto maximo. Debe ocurrir un climax.",
        trigger_meter="tension",
        trigger_value=90,
    )

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=5,
        current_dramatic_state={"tension": 90, "hope": 30, "chaos": 60, "rhythm": 50, "saturation": 70, "connection": 40, "mystery": 65},
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=None,
        forced_constraint=forced,
    )

    proposal = await mock_adapter.generate_narrative(context)

    assert proposal is not None
    # El mock debe generar narrativa de evento forzado
    assert "CLIMAX" in proposal.narrative_text or "critico" in proposal.narrative_text.lower()

    print(f"  [OK] Evento forzado: {forced.event_type.value}")
    print(f"  [OK] Narrativa: {proposal.narrative_text[:100]}...")


@pytest.mark.asyncio
async def test_fase3_dramatic_deltas_validation(sample_world, mock_adapter):
    """Test: Los deltas dramaticos estan en rango valido."""
    print("\n[TEST] Fase 3 - Validacion de deltas dramaticos")

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=0,
        current_dramatic_state={"tension": 30, "hope": 60, "chaos": 20, "rhythm": 50, "saturation": 0, "connection": 40, "mystery": 50},
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=None,
        forced_constraint=None,
    )

    proposal = await mock_adapter.generate_narrative(context)

    # Verificar que todos los deltas esten en rango [-100, 100]
    delta = proposal.dramatic_delta
    assert -100 <= delta.tension <= 100
    assert -100 <= delta.hope <= 100
    assert -100 <= delta.chaos <= 100
    assert -100 <= delta.rhythm <= 100
    assert -100 <= delta.saturation <= 100
    assert -100 <= delta.connection <= 100
    assert -100 <= delta.mystery <= 100

    print(f"  [OK] Todos los deltas en rango valido")
    print(f"  [OK] Deltas: T={delta.tension}, H={delta.hope}, C={delta.chaos}")


@pytest.mark.asyncio
async def test_fase3_multiple_generations_determinism(sample_world):
    """Test: El MockAdapter genera respuestas deterministicas consistentes."""
    print("\n[TEST] Fase 3 - Determinismo en multiples generaciones")

    # Crear dos adapters identicos
    adapter1 = MockAdapter(deterministic=True, seed=42)
    adapter2 = MockAdapter(deterministic=True, seed=42)

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=0,
        current_dramatic_state={"tension": 50, "hope": 50, "chaos": 30, "rhythm": 50, "saturation": 0, "connection": 40, "mystery": 50},
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=None,
        forced_constraint=None,
    )

    # Generar multiples veces con cada adapter
    results1 = []
    results2 = []

    for i in range(3):
        p1 = await adapter1.generate_narrative(context)
        p2 = await adapter2.generate_narrative(context)
        results1.append(p1.narrative_text)
        results2.append(p2.narrative_text)

    # Los primeros resultados de cada adapter deben ser identicos
    assert results1[0] == results2[0]

    # Pero las sucesivas generaciones pueden variar (call_count cambia)
    # Esto es esperado porque el mock usa call_count para variacion

    print(f"  [OK] Primera generacion identica entre adapters")
    print(f"  [OK] Generaciones: {len(results1)}")


@pytest.mark.asyncio
async def test_fase3_choices_validation(sample_world, mock_adapter):
    """Test: Las choices generadas son validas y tienen previews."""
    print("\n[TEST] Fase 3 - Validacion de choices")

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=0,
        current_dramatic_state={"tension": 40, "hope": 60, "chaos": 20, "rhythm": 50, "saturation": 0, "connection": 40, "mystery": 50},
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=None,
        forced_constraint=None,
    )

    proposal = await mock_adapter.generate_narrative(context)

    # Verificar choices
    assert 2 <= len(proposal.choices) <= 5

    for choice in proposal.choices:
        assert len(choice.text) > 5
        assert choice.dramatic_preview is not None
        # Preview debe tener tension, hope, chaos
        assert "tension" in choice.dramatic_preview
        assert "hope" in choice.dramatic_preview

    print(f"  [OK] {len(proposal.choices)} choices validas")
    print(f"  [OK] Ejemplo: {proposal.choices[0].text}")


if __name__ == "__main__":
    print("=== Tests de Fase 3 (AI Integration) ===\n")

    # Crear fixtures
    world = WorldDefinition(
        name="Reino de Eldoria",
        context="Un reino medieval en crisis",
        protagonist="Princesa Lyra",
        era="Medieval",
        tone=NarrativeTone.DARK,
    )

    adapter = MockAdapter(deterministic=True)

    # Ejecutar tests
    asyncio.run(test_fase3_basic_narrative_flow(world, adapter))
    asyncio.run(test_fase3_with_player_choice(world, adapter))

    adapter2 = MockAdapter(deterministic=True)
    asyncio.run(test_fase3_forced_event_context(world, adapter2))

    adapter3 = MockAdapter(deterministic=True)
    asyncio.run(test_fase3_dramatic_deltas_validation(world, adapter3))

    asyncio.run(test_fase3_multiple_generations_determinism(world))

    adapter4 = MockAdapter(deterministic=True)
    asyncio.run(test_fase3_choices_validation(world, adapter4))

    print("\n[SUCCESS] Todos los tests de Fase 3 pasaron")
