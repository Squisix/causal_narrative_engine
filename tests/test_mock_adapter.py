"""
tests/test_mock_adapter.py - Tests del MockAdapter

No requiere API key. Verifica que el MockAdapter:
1. Genere respuestas validas
2. Sea determinista cuando se configura asi
3. Funcione con el motor completo

Ejecutar:
    pytest tests/test_mock_adapter.py -v
"""

import pytest
import asyncio

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.interfaces.ai_adapter import NarrativeContext
from adapters.mock_adapter import MockAdapter


@pytest.fixture
def sample_world():
    """Mundo de prueba simple."""
    return WorldDefinition(
        name="Reino de Prueba",
        context="Un reino medieval de prueba",
        protagonist="El Heroe",
        era="Medieval",
        tone=NarrativeTone.ADVENTUROUS,
    )


@pytest.fixture
def mock_adapter():
    """MockAdapter determinista."""
    return MockAdapter(deterministic=True, seed=42)


@pytest.mark.asyncio
async def test_mock_adapter_basic_generation(sample_world, mock_adapter):
    """Test: El MockAdapter genera respuestas validas."""
    print("\n[TEST] MockAdapter - Generacion basica")

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

    # Generar narrativa
    proposal = await mock_adapter.generate_narrative(context)

    # Verificar que la respuesta sea valida
    assert proposal is not None
    assert len(proposal.narrative_text) > 50
    assert len(proposal.summary) > 10
    assert len(proposal.choices) >= 2
    assert proposal.dramatic_delta is not None

    print(f"  [OK] Narrativa: {proposal.narrative_text[:80]}...")
    print(f"  [OK] Summary: {proposal.summary}")
    print(f"  [OK] Choices: {len(proposal.choices)}")
    print(f"  [OK] Dramatic delta: tension={proposal.dramatic_delta.tension}")


@pytest.mark.asyncio
async def test_mock_adapter_determinism(sample_world):
    """Test: El MockAdapter es determinista cuando se configura asi."""
    print("\n[TEST] MockAdapter - Determinismo")

    # Crear dos adapters con misma config
    adapter1 = MockAdapter(deterministic=True, seed=42)
    adapter2 = MockAdapter(deterministic=True, seed=42)

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=0,
        current_dramatic_state={"tension": 50, "hope": 50, "chaos": 20, "rhythm": 50, "saturation": 0, "connection": 40, "mystery": 50},
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=None,
        forced_constraint=None,
    )

    # Generar con ambos
    proposal1 = await adapter1.generate_narrative(context)
    proposal2 = await adapter2.generate_narrative(context)

    # Deben ser identicas
    assert proposal1.narrative_text == proposal2.narrative_text
    assert proposal1.summary == proposal2.summary
    assert proposal1.choices == proposal2.choices

    print("  [OK] Las respuestas son identicas (determinismo verificado)")


@pytest.mark.asyncio
async def test_mock_adapter_with_player_choice(sample_world, mock_adapter):
    """Test: El MockAdapter maneja decisiones del jugador."""
    print("\n[TEST] MockAdapter - Con decision de jugador")

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=1,
        current_dramatic_state={"tension": 60, "hope": 50, "chaos": 25, "rhythm": 50, "saturation": 5, "connection": 40, "mystery": 50},
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice="Explorar el bosque oscuro",
        forced_constraint=None,
    )

    proposal = await mock_adapter.generate_narrative(context)

    assert proposal is not None
    # La narrativa debe mencionar o referenciar la decision del jugador
    # El mock incluye el texto de la choice en el summary
    assert "explorar" in proposal.summary.lower() or "bosque" in proposal.summary.lower()

    print(f"  [OK] Narrativa generada tras decision: {proposal.summary}")


@pytest.mark.asyncio
async def test_mock_adapter_stats(sample_world, mock_adapter):
    """Test: El MockAdapter mantiene estadisticas."""
    print("\n[TEST] MockAdapter - Estadisticas")

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

    # Generar varias veces
    for i in range(5):
        await mock_adapter.generate_narrative(context)

    stats = mock_adapter.get_stats()

    assert stats["total_calls"] == 5
    assert stats["deterministic"] is True

    print(f"  [OK] Stats: {stats}")


@pytest.mark.asyncio
async def test_mock_adapter_error_mode(sample_world):
    """Test: El MockAdapter puede forzar errores para testing."""
    print("\n[TEST] MockAdapter - Modo error")

    # Adapter configurado para generar errores
    error_adapter = MockAdapter(deterministic=True, force_errors=True)

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

    # Generar (deberia retornar algo invalido)
    proposal = await error_adapter.generate_narrative(context)

    # La respuesta existe pero tiene problemas
    assert proposal is not None
    # El narrative sera muy corto (viola validacion)
    assert len(proposal.narrative_text) < 50

    print("  [OK] Modo error funciona correctamente")


if __name__ == "__main__":
    print("=== Tests de MockAdapter ===\n")

    # Ejecutar tests manualmente
    world = WorldDefinition(
        name="Reino de Prueba",
        context="Un reino medieval de prueba",
        protagonist="El Heroe",
        era="Medieval",
        tone=NarrativeTone.ADVENTUROUS,
    )
    adapter = MockAdapter(deterministic=True)

    # Test basico
    asyncio.run(test_mock_adapter_basic_generation(world, adapter))

    # Test determinismo
    asyncio.run(test_mock_adapter_determinism(world))

    # Test con choice
    adapter2 = MockAdapter(deterministic=True)
    asyncio.run(test_mock_adapter_with_player_choice(world, adapter2))

    # Test stats
    adapter3 = MockAdapter(deterministic=True)
    asyncio.run(test_mock_adapter_stats(world, adapter3))

    # Test error mode
    asyncio.run(test_mock_adapter_error_mode(world))

    print("\n[SUCCESS] Todos los tests del MockAdapter pasaron")
