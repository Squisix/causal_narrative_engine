"""
tests/test_anthropic_adapter.py - AnthropicAdapter Tests (REAL API)

IMPORTANT: These tests connect to the Anthropic API and consume tokens.
They do not run by default. They only run if:

1. You have ANTHROPIC_API_KEY configured
2. You run: pytest -m anthropic_api

To configure:
    1. Copy .env.example to .env
    2. Add your real API key
    3. Run: pytest -m anthropic_api -v

Estimated cost: ~$0.01 USD per full run
"""

import pytest
import os
from pathlib import Path

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.interfaces.ai_adapter import NarrativeContext
from adapters.anthropic_adapter import AnthropicAdapter


# Custom marker for tests that require an API key
pytestmark = pytest.mark.anthropic_api


def check_api_key():
    """Verifies that the API key is configured."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip(
            "ANTHROPIC_API_KEY is not configured. "
            "Set up your .env to run these tests."
        )
    if api_key.startswith("sk-ant-api03-tu-api-key"):
        pytest.skip(
            "ANTHROPIC_API_KEY is the example value. "
            "Replace it with your real Anthropic key."
        )
    return api_key


@pytest.fixture
def sample_world():
    """Test world."""
    lyra = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100},
    )

    return WorldDefinition(
        name="Test Kingdom",
        context="A medieval kingdom in crisis",
        protagonist="Princess Lyra",
        era="Medieval",
        tone=NarrativeTone.DARK,
        initial_entities=[lyra],
    )


@pytest.fixture
def anthropic_adapter():
    """Real AnthropicAdapter."""
    check_api_key()
    return AnthropicAdapter(
        temperature=0.7,
        max_tokens=1024,  # Reduced to save costs in tests
    )


@pytest.mark.asyncio
async def test_anthropic_basic_generation(sample_world, anthropic_adapter):
    """Test: The AnthropicAdapter generates real narrative."""
    print("\n[TEST] Anthropic - Basic generation (REAL API)")

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

    # Generate with Claude
    proposal = await anthropic_adapter.generate_narrative(context)

    # Verify response
    assert proposal is not None
    assert len(proposal.narrative_text) > 50
    assert len(proposal.choices) >= 2
    assert proposal.dramatic_delta is not None

    print(f"  [OK] Narrative generated: {len(proposal.narrative_text)} characters")
    print(f"  [OK] Choices: {len(proposal.choices)}")
    print(f"  [OK] Example: {proposal.narrative_text[:100]}...")

    # Verify stats
    stats = anthropic_adapter.get_stats()
    assert stats["total_calls"] == 1
    assert stats["total_tokens_used"] > 0

    print(f"  [OK] Tokens used: {stats['total_tokens_used']}")


@pytest.mark.asyncio
async def test_anthropic_with_player_choice(sample_world, anthropic_adapter):
    """Test: Claude responds to player decisions."""
    print("\n[TEST] Anthropic - With player decision (REAL API)")

    player_choice = "Investigate the castle at night"

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
    # Claude should mention the decision in the narrative or causal_reason
    text_to_check = (proposal.narrative_text + " " + proposal.causal_reason).lower()
    assert "investig" in text_to_check or "castle" in text_to_check or "night" in text_to_check

    print(f"  [OK] Claude incorporated the player's decision")
    print(f"  [OK] Causal reason: {proposal.causal_reason[:80]}...")


@pytest.mark.asyncio
async def test_anthropic_validation(sample_world, anthropic_adapter):
    """Test: Claude's responses pass validation."""
    print("\n[TEST] Anthropic - Response validation (REAL API)")

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

    # Verify that all fields are valid
    assert 50 <= len(proposal.narrative_text) <= 2000
    assert 10 <= len(proposal.summary) <= 200
    assert 2 <= len(proposal.choices) <= 5

    # Verify dramatic deltas are in range
    delta = proposal.dramatic_delta
    assert -100 <= delta.tension <= 100
    assert -100 <= delta.hope <= 100
    assert -100 <= delta.chaos <= 100

    print(f"  [OK] Valid response within limits")
    print(f"  [OK] Dramatic deltas: T={delta.tension}, H={delta.hope}, C={delta.chaos}")


@pytest.mark.asyncio
async def test_anthropic_stats_tracking(sample_world, anthropic_adapter):
    """Test: The adapter tracks statistics correctly."""
    print("\n[TEST] Anthropic - Statistics tracking (REAL API)")

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

    # Generate 2 times
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
    print("=== AnthropicAdapter Tests (REAL API) ===\n")
    print("WARNING: These tests consume Anthropic API tokens")
    print("Run with: pytest tests/test_anthropic_adapter.py -m anthropic_api -v\n")
