"""
tests/test_anthropic_adapter.py - Tests del AnthropicAdapter (REAL API)

IMPORTANTE: Estos tests se conectan a la API de Anthropic y consumen tokens.
No se ejecutan por defecto. Solo corren si:

1. Tienes ANTHROPIC_API_KEY configurada
2. Ejecutas: pytest -m anthropic_api

Para configurar:
    1. Copia .env.example a .env
    2. Agrega tu API key real
    3. Ejecuta: pytest -m anthropic_api -v

Costo estimado: ~$0.01 USD por ejecucion completa
"""

import pytest
import os
from pathlib import Path

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.interfaces.ai_adapter import NarrativeContext
from adapters.anthropic_adapter import AnthropicAdapter


# Marker personalizado para tests que requieren API key
pytestmark = pytest.mark.anthropic_api


def check_api_key():
    """Verifica que la API key este configurada."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip(
            "ANTHROPIC_API_KEY no esta configurada. "
            "Configura tu .env para ejecutar estos tests."
        )
    if api_key.startswith("sk-ant-api03-tu-api-key"):
        pytest.skip(
            "ANTHROPIC_API_KEY es el valor de ejemplo. "
            "Reemplazala con tu key real de Anthropic."
        )
    return api_key


@pytest.fixture
def sample_world():
    """Mundo de prueba."""
    lyra = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100},
    )

    return WorldDefinition(
        name="Reino de Prueba",
        context="Un reino medieval en crisis",
        protagonist="Princesa Lyra",
        era="Medieval",
        tone=NarrativeTone.DARK,
        initial_entities=[lyra],
    )


@pytest.fixture
def anthropic_adapter():
    """AnthropicAdapter real."""
    check_api_key()
    return AnthropicAdapter(
        temperature=0.7,
        max_tokens=1024,  # Reducido para ahorrar costos en tests
    )


@pytest.mark.asyncio
async def test_anthropic_basic_generation(sample_world, anthropic_adapter):
    """Test: El AnthropicAdapter genera narrativa real."""
    print("\n[TEST] Anthropic - Generacion basica (REAL API)")

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

    # Generar con Claude
    proposal = await anthropic_adapter.generate_narrative(context)

    # Verificar respuesta
    assert proposal is not None
    assert len(proposal.narrative_text) > 50
    assert len(proposal.choices) >= 2
    assert proposal.dramatic_delta is not None

    print(f"  [OK] Narrativa generada: {len(proposal.narrative_text)} caracteres")
    print(f"  [OK] Choices: {len(proposal.choices)}")
    print(f"  [OK] Ejemplo: {proposal.narrative_text[:100]}...")

    # Verificar stats
    stats = anthropic_adapter.get_stats()
    assert stats["total_calls"] == 1
    assert stats["total_tokens_used"] > 0

    print(f"  [OK] Tokens usados: {stats['total_tokens_used']}")


@pytest.mark.asyncio
async def test_anthropic_with_player_choice(sample_world, anthropic_adapter):
    """Test: Claude responde a decisiones del jugador."""
    print("\n[TEST] Anthropic - Con decision de jugador (REAL API)")

    player_choice = "Investigar el castillo de noche"

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=1,
        current_dramatic_state={
            "tension": 50,
            "hope": 55,
            "chaos": 30,
            "rhythm": 50,
            "saturation": 10,
            "connection": 40,
            "mystery": 60,
        },
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=player_choice,
        forced_constraint=None,
    )

    proposal = await anthropic_adapter.generate_narrative(context)

    assert proposal is not None
    # Claude deberia mencionar la decision en la narrativa o causal_reason
    text_to_check = (proposal.narrative_text + " " + proposal.causal_reason).lower()
    assert "investig" in text_to_check or "castillo" in text_to_check or "noche" in text_to_check

    print(f"  [OK] Claude incorporo la decision del jugador")
    print(f"  [OK] Causal reason: {proposal.causal_reason[:80]}...")


@pytest.mark.asyncio
async def test_anthropic_validation(sample_world, anthropic_adapter):
    """Test: Las respuestas de Claude pasan validacion."""
    print("\n[TEST] Anthropic - Validacion de respuestas (REAL API)")

    context = NarrativeContext(
        world_definition=sample_world,
        current_depth=0,
        current_dramatic_state={
            "tension": 40,
            "hope": 60,
            "chaos": 25,
            "rhythm": 50,
            "saturation": 5,
            "connection": 45,
            "mystery": 55,
        },
        current_entity_states={},
        current_world_vars={},
        commit_chain=[],
        player_choice=None,
        forced_constraint=None,
    )

    proposal = await anthropic_adapter.generate_narrative(context)

    # Verificar que todos los campos sean validos
    assert 50 <= len(proposal.narrative_text) <= 2000
    assert 10 <= len(proposal.summary) <= 200
    assert 2 <= len(proposal.choices) <= 5

    # Verificar deltas dramaticos en rango
    delta = proposal.dramatic_delta
    assert -100 <= delta.tension <= 100
    assert -100 <= delta.hope <= 100
    assert -100 <= delta.chaos <= 100

    print(f"  [OK] Respuesta valida y dentro de limites")
    print(f"  [OK] Dramatic deltas: T={delta.tension}, H={delta.hope}, C={delta.chaos}")


@pytest.mark.asyncio
async def test_anthropic_stats_tracking(sample_world, anthropic_adapter):
    """Test: El adapter trackea estadisticas correctamente."""
    print("\n[TEST] Anthropic - Tracking de estadisticas (REAL API)")

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

    # Generar 2 veces
    await anthropic_adapter.generate_narrative(context)
    await anthropic_adapter.generate_narrative(context)

    stats = anthropic_adapter.get_stats()

    assert stats["total_calls"] == 2
    assert stats["failed_calls"] == 0
    assert stats["success_rate"] == 1.0
    assert stats["total_tokens_used"] > 0
    assert stats["avg_tokens_per_call"] > 0

    print(f"  [OK] Total calls: {stats['total_calls']}")
    print(f"  [OK] Total tokens: {stats['total_tokens_used']}")
    print(f"  [OK] Avg tokens/call: {stats['avg_tokens_per_call']:.0f}")


if __name__ == "__main__":
    print("=== Tests de AnthropicAdapter (REAL API) ===\n")
    print("ADVERTENCIA: Estos tests consumen tokens de Anthropic API")
    print("Ejecuta con: pytest tests/test_anthropic_adapter.py -m anthropic_api -v\n")
