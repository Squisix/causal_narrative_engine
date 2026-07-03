"""
examples/fase2_example.py — Complete Phase 2 Example

Demonstrates:
- Creating a WorldDefinition
- Saving it to PostgreSQL
- Creating narrative commits
- Validating the causal graph
- Navigating the trunk

Requirements:
- PostgreSQL running: `docker-compose up -d`
- Migrations applied: `alembic upgrade head`

Run:
    python examples/fase2_example.py
"""

import asyncio
from datetime import datetime

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.models.event import (
    NarrativeEvent, EventType, CausalEdge,
    EntityDelta, DramaticDelta
)
from cne_core.models.commit import NarrativeCommit, Branch

from persistence.database import DatabaseConfig
from persistence.repositories.postgresql_repository import PostgreSQLRepository


async def main():
    print("=" * 70)
    print("CNE — Phase 2 Example: PostgreSQL Persistence")
    print("=" * 70)

    # -- 1. Configure DB -------------------------------------------------------
    print("\n[1/7] Configuring database...")
    db_config = DatabaseConfig(
        "postgresql+asyncpg://cne_user@localhost:5433/cne_db",
        echo=False  # echo=True to see SQL queries
    )
    repo = PostgreSQLRepository(db_config)
    print("[OK] Connected to PostgreSQL")

    # -- 2. Create WorldDefinition ---------------------------------------------
    print("\n[2/7] Creating narrative world...")

    # Initial entities
    hero = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={
            "health": 100,
            "courage": 85,
            "wisdom": 70,
            "alive": True,
            "role": "Guardian of the Kingdom"
        }
    )

    villain = Entity(
        name="Malachar",
        entity_type=EntityType.CHARACTER,
        attributes={
            "power": 95,
            "influence": 80,
            "corruption": 90,
            "alive": True,
            "role": "Dark Lord"
        }
    )

    artifact = Entity(
        name="The Crystal of Truth",
        entity_type=EntityType.ARTIFACT,
        attributes={
            "power_level": 100,
            "corrupted": False,
            "location": "Ancient Temple"
        }
    )

    # WorldDefinition
    world = WorldDefinition(
        name="The Kingdom of Shadows",
        context=(
            "A medieval kingdom where dark magic threatens to destroy everything. "
            "The Crystal of Truth is the only hope, but it is guarded "
            "by ancient forces that cannot distinguish between good and evil."
        ),
        protagonist=(
            "Lyra, a guardian of the kingdom who was betrayed by those "
            "she swore to protect. Now she must decide whether to save the kingdom "
            "or let it fall into darkness."
        ),
        era="Medieval fantasy, year 843 of the Age of Kings",
        tone=NarrativeTone.DARK,
        antagonist="Malachar the Corrupt, a former fallen hero",
        rules="Dark magic has a price: each spell corrupts the user's soul.",
        constraints=[
            "No resurrections — death is permanent",
            "Magic has irreversible consequences",
            "Past decisions condition future options",
        ],
        initial_entities=[hero, villain, artifact],
        dramatic_config={
            "tension": 45,
            "hope": 50,
            "chaos": 30,
            "rhythm": 50,
            "saturation": 0,
            "connection": 40,
            "mystery": 70,
        },
        max_depth=100,
    )

    await repo.save_world(world)
    print(f"[OK] World saved: '{world.name}' (ID: {world.id[:8]}...)")
    print(f"   Initial entities: {len(world.initial_entities)}")
    print(f"   Tone: {world.tone.value}")

    # -- 3. Create main branch -------------------------------------------------
    print("\n[3/7] Creating narrative branch...")

    branch = Branch(
        world_id=world.id,
        origin_commit_id="root",  # Will be updated when we create the root commit
        name="Hero's Path",
        description="Lyra accepts her destiny and faces Malachar",
    )
    await repo.save_branch(branch)
    print(f"[OK] Branch created: '{branch.name}' (ID: {branch.id[:8]}...)")

    # -- 4. Create narrative commits -------------------------------------------
    print("\n[4/7] Building story...")

    # Commit 0: Beginning
    event0 = NarrativeEvent(
        commit_id="pending",
        event_type=EventType.DECISION,
        narrative_text=(
            "The kingdom is in danger. Malachar has awakened and threatens to "
            "plunge the world into eternal darkness. Lyra, exiled years ago "
            "for a betrayal she never committed, must decide whether to return to "
            "save those who abandoned her."
        ),
        summary="Lyra must decide whether to return to the kingdom.",
        depth=0,
        dramatic_delta=DramaticDelta(tension=5, mystery=10, connection=-5),
    )

    commit0 = NarrativeCommit(
        world_id=world.id,
        event_id=event0.id,
        depth=0,
        narrative_text=event0.narrative_text,
        summary=event0.summary,
        branch_id=branch.id,
        dramatic_snapshot=world.dramatic_config.copy(),
    )

    event0.commit_id = commit0.id
    await repo.save_commit(commit0)
    await repo.save_event(event0)
    await repo.save_dramatic_state(commit0.id, world.dramatic_config)
    print(f"   [Chapter 0] {commit0.summary}")

    # Commit 1: Lyra decides to return
    dramatic_state_1 = {
        "tension": 50,
        "hope": 45,
        "chaos": 30,
        "rhythm": 55,
        "saturation": 5,
        "connection": 35,
        "mystery": 80,
    }

    event1 = NarrativeEvent(
        commit_id="pending",
        event_type=EventType.DECISION,
        narrative_text=(
            "Lyra rides toward the capital. As she approaches, memories "
            "of the betrayal come flooding back. But duty is stronger than resentment. "
            "Upon arriving at the palace, she discovers that the king has been murdered and Malachar "
            "already controls most of the kingdom."
        ),
        summary="Lyra returns and discovers that the king is dead.",
        triggered_by_decision="Return to the kingdom",
        caused_by=[event0.id],
        depth=1,
        dramatic_delta=DramaticDelta(tension=5, hope=-5, mystery=10),
    )

    commit1 = NarrativeCommit(
        world_id=world.id,
        event_id=event1.id,
        depth=1,
        parent_id=commit0.id,
        choice_text="Return to the kingdom",
        narrative_text=event1.narrative_text,
        summary=event1.summary,
        branch_id=branch.id,
        dramatic_snapshot=dramatic_state_1,
    )

    event1.commit_id = commit1.id
    await repo.save_commit(commit1)
    await repo.save_event(event1)
    await repo.save_dramatic_state(commit1.id, dramatic_state_1)

    # Create causal edge
    edge_0_1 = CausalEdge(
        cause_event_id=event0.id,
        effect_event_id=event1.id,
    )
    await repo.save_causal_edge(edge_0_1)
    print(f"   [Chapter 1] {commit1.summary}")

    # Commit 2: Lyra finds the Crystal
    dramatic_state_2 = {
        "tension": 60,
        "hope": 55,
        "chaos": 35,
        "rhythm": 60,
        "saturation": 10,
        "connection": 40,
        "mystery": 65,
    }

    # Delta: Lyra obtains the Crystal
    delta_crystal = EntityDelta(
        entity_id=artifact.id,
        entity_name=artifact.name,
        attribute="location",
        old_value="Ancient Temple",
        new_value="In Lyra's possession",
    )

    event2 = NarrativeEvent(
        commit_id="pending",
        event_type=EventType.DECISION,
        narrative_text=(
            "After weeks of searching, Lyra finds the Ancient Temple. "
            "The Crystal of Truth glows with its own light, but upon touching it, "
            "she senses a dark presence. The Crystal shows her visions of the past: "
            "the betrayal that exiled her was orchestrated by Malachar from the shadows."
        ),
        summary="Lyra obtains the Crystal and discovers the truth.",
        triggered_by_decision="Search for the Crystal of Truth",
        caused_by=[event1.id],
        entity_deltas=[delta_crystal],
        depth=2,
        dramatic_delta=DramaticDelta(tension=10, hope=10, mystery=-15, connection=5),
    )

    commit2 = NarrativeCommit(
        world_id=world.id,
        event_id=event2.id,
        depth=2,
        parent_id=commit1.id,
        choice_text="Search for the Crystal of Truth",
        narrative_text=event2.narrative_text,
        summary=event2.summary,
        branch_id=branch.id,
        dramatic_snapshot=dramatic_state_2,
    )

    event2.commit_id = commit2.id
    await repo.save_commit(commit2)
    await repo.save_event(event2)
    await repo.save_dramatic_state(commit2.id, dramatic_state_2)

    edge_1_2 = CausalEdge(
        cause_event_id=event1.id,
        effect_event_id=event2.id,
    )
    await repo.save_causal_edge(edge_1_2)
    print(f"   [Chapter 2] {commit2.summary}")

    print(f"\n[OK] Story created: {commit2.depth + 1} chapters")

    # -- 5. Retrieve trunk -----------------------------------------------------
    print("\n[5/7] Retrieving complete story...")

    trunk = await repo.get_trunk(commit2.id, max_depth=100)
    print(f"[OK] Trunk retrieved: {len(trunk)} commits")
    for i, commit in enumerate(trunk):
        print(f"   [{i}] {commit.summary}")

    # -- 6. Validate causal graph ----------------------------------------------
    print("\n[6/7] Validating causal graph...")

    # Verify that path event0 -> event1 -> event2 exists
    path_exists = await repo.check_causal_path_exists(event0.id, event2.id)
    print(f"[OK] Causal path event0 -> event2: {'Exists' if path_exists else 'Does not exist'}")

    # Attempt to create cycle (should fail)
    try:
        edge_2_0 = CausalEdge(
            cause_event_id=event2.id,
            effect_event_id=event0.id,
        )
        await repo.save_causal_edge(edge_2_0)
        print("[ERROR] A cycle was allowed to be created")
    except ValueError as e:
        print(f"[OK] Cycle detected correctly: {str(e)[:60]}...")

    # -- 7. Dramatic state -----------------------------------------------------
    print("\n[7/7] Dramatic analysis...")

    for i, commit in enumerate(trunk):
        state = await repo.get_dramatic_state(commit.id)
        if state:
            print(f"   [Ch.{i}] T={state['tension']:>2} H={state['hope']:>2} M={state['mystery']:>2}")

    # -- Summary ---------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 2 SUMMARY")
    print("=" * 70)
    print(f"[OK] World persisted: {world.name}")
    print(f"[OK] Commits saved: {len(trunk)}")
    print(f"[OK] Causal graph validated (no cycles)")
    print(f"[OK] Dramatic vector tracked")
    print(f"[OK] Entity deltas recorded")
    print("\nNext steps:")
    print("  - Phase 3: Connect AI (Anthropic/Claude)")
    print("  - Phase 4: REST API with FastAPI")
    print("  - Phase 5: Public release + docs")
    print("=" * 70)

    # Cleanup
    await db_config.dispose()


if __name__ == "__main__":
    asyncio.run(main())
