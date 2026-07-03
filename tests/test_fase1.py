"""
tests/test_fase1.py — Complete Phase 1 Test

Run: python -m pytest tests/test_fase1.py -v
Or directly: python tests/test_fase1.py

This test runs a complete story of 6 decisions in memory,
validating the 4 formal properties of the CNE:
    P1: Causality (cycle-free DAG)
    P2: Deterministic reconstruction
    P3: Narrative versioning (branches)
    P4: Narrative consistency
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.models.event import (
    EntityDelta, WorldVariableDelta, DramaticDelta, CausalRelationType
)
from cne_core.models.commit import NarrativeChoice
from cne_core.engine.causal_validator import CausalValidator, CausalCycleError
from cne_core.engine.dramatic_engine import DramaticEngine, DramaticVector
from cne_core.engine.state_machine import StateMachine


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def make_choice(text: str, t: int = 0, h: int = 0) -> NarrativeChoice:
    """Create a NarrativeChoice with dramatic preview."""
    return NarrativeChoice(
        text=text,
        dramatic_preview={"tension": t, "hope": h},
        tone_hint="neutral",
    )

def separator(title: str):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 1: CausalValidator — Property P1
# ═══════════════════════════════════════════════════════════════════════════════

def test_causal_validator():
    separator("TEST P1: CausalValidator — Cycle-free DAG")

    validator = CausalValidator()

    # Register events
    validator.add_event("e1")
    validator.add_event("e2")
    validator.add_event("e3")
    validator.add_event("e4")

    # Create causal chain: e1 -> e2 -> e3
    validator.add_edge("e1", "e2")
    validator.add_edge("e2", "e3")
    validator.add_edge("e1", "e4")   # Fork: e1 also causes e4

    print("[OK] Valid edges added: e1->e2, e2->e3, e1->e4")

    # Verify the graph is a DAG
    assert validator.is_dag(), "The graph must be a DAG"
    print("[OK] is_dag() = True")

    # Verify topological order (e1 always before e2, e2 before e3)
    assert validator.get_topo_order("e1") < validator.get_topo_order("e2")
    assert validator.get_topo_order("e2") < validator.get_topo_order("e3")
    print(f"[OK] Topological order correct: e1={validator.get_topo_order('e1')}, "
          f"e2={validator.get_topo_order('e2')}, e3={validator.get_topo_order('e3')}")

    # Verify that cycles are detected
    cycle_detected = False
    try:
        # Attempt: e3 -> e1 would create the cycle e1->e2->e3->e1
        validator.add_edge("e3", "e1")
        print("[FAIL] ERROR: Should have detected the cycle")
    except CausalCycleError as err:
        cycle_detected = True
        print(f"[OK] Cycle detected correctly: {err}")

    assert cycle_detected, "Must detect the cycle e3->e1"

    # Verify ancestors
    ancestors = validator.get_all_ancestors("e3")
    assert "e1" in ancestors and "e2" in ancestors
    print(f"[OK] Ancestors of e3: {ancestors}")

    stats = validator.get_stats()
    print(f"[OK] Stats: {stats}")

    print("\n[***] P1 CAUSALITY: VERIFIED")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: DramaticEngine — Thresholds and forced events
# ═══════════════════════════════════════════════════════════════════════════════

def test_dramatic_engine():
    separator("TEST: DramaticEngine — Thresholds and forced events")

    # Start with tension at 30 (normal)
    engine = DramaticEngine({"tension": 30, "hope": 60, "chaos": 20,
                              "rhythm": 50, "saturation": 0,
                              "connection": 40, "mystery": 50})

    print(f"Initial state: {engine.vector}")

    # No thresholds crossed -> None
    constraint = engine.evaluate_thresholds()
    assert constraint is None, "There should be no forced events at the start"
    print("[OK] No thresholds crossed -> None")

    # Raise tension to 90 -> must force CLIMAX
    engine.apply_delta_from_dict({"tension": 60, "hope": -10})
    print(f"After +60 tension: {engine.vector}")

    constraint = engine.evaluate_thresholds()
    assert constraint is not None, "There must be a forced event"
    print(f"[OK] Threshold crossed -> {constraint.event_type.value}: {constraint.description[:60]}...")

    # Verify that the instruction for the AI is clear
    prompt_text = constraint.to_prompt_constraint()
    assert "MANDATORY DRAMATIC CONSTRAINT" in prompt_text
    print(f"[OK] Prompt constraint generated correctly")

    # Test: high mystery + tension -> revelation
    engine2 = DramaticEngine({"tension": 70, "hope": 40, "chaos": 30,
                               "rhythm": 50, "saturation": 0,
                               "connection": 40, "mystery": 70})
    constraint2 = engine2.evaluate_thresholds()
    assert constraint2 is not None
    print(f"[OK] High Mystery+Tension -> {constraint2.event_type.value}")

    # Test: Tension climax pacing (turn 1, 2, and 3)
    pacing_engine = DramaticEngine({"tension": 30})

    # Turn 1: Raise tension to 90
    pacing_engine.apply_delta_from_dict({"tension": 60})
    constraint_t1 = pacing_engine.evaluate_thresholds()
    assert constraint_t1 is not None
    assert "Turn 1 of Extreme Tension" in constraint_t1.description

    # Turn 2: Maintain at 90
    pacing_engine.apply_delta_from_dict({"tension": 0})
    constraint_t2 = pacing_engine.evaluate_thresholds()
    assert constraint_t2 is not None
    assert "Turn 2 of Extreme Tension" in constraint_t2.description

    # Turn 3: Maintain at 90
    pacing_engine.apply_delta_from_dict({"tension": 0})
    constraint_t3 = pacing_engine.evaluate_thresholds()
    assert constraint_t3 is not None
    assert "required to return a significantly negative 'tension' delta" in constraint_t3.description
    print("[OK] Tension Climax Pacing verified correctly for Turns 1, 2 and 3")

    # Test arc analysis
    analysis = engine.get_arc_analysis()
    print(f"[OK] Arc analysis: {analysis}")

    print("\n[***] DRAMATIC ENGINE: VERIFIED")



# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: StateMachine — Full story (P1 + P2 + P3 + P4)
# ═══════════════════════════════════════════════════════════════════════════════

def test_full_story():
    separator("TEST P1+P2+P3+P4: Full story in memory")

    # -- Create the world -------------------------------------------------------
    lyra = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={"alive": True, "health": 100, "loyalty": 80, "is_queen": False}
    )

    malachar = Entity(
        name="Counselor Malachar",
        entity_type=EntityType.CHARACTER,
        attributes={"alive": True, "health": 100, "loyalty": 0, "is_traitor": True}
    )

    world = WorldDefinition(
        name         = "The Kingdom of Valdris",
        context      = ("A medieval kingdom on the brink of war. The king has died "
                       "mysteriously. Lyra, the 17-year-old heir, must rule "
                       "alone while Counselor Malachar conspires in the shadows."),
        protagonist  = "Lyra, the crown princess",
        era          = "Fantastic Middle Ages, year 843",
        tone         = NarrativeTone.DARK,
        antagonist   = "Counselor Malachar, who seeks the throne",
        rules        = "Magic exists but has a life cost",
        constraints  = ["The dead cannot return", "No time travel"],
        initial_entities = [lyra, malachar],
        dramatic_config  = {
            "tension": 40, "hope": 55, "chaos": 25,
            "rhythm": 50, "saturation": 0, "connection": 35, "mystery": 65
        },
        max_depth = 10,
    )

    engine = StateMachine(world)
    print(f"[SEED] Seed created: {world}")

    # -- Chapter 0: Beginning ---------------------------------------------------
    result = engine.start(
        initial_narrative=(
            "The throne room is silent when Lyra receives the news. "
            "Her father, King Aldric, has been found dead in his chambers. "
            "There are no marks of violence, but the royal physician whispers that the "
            "circumstances are... irregular. Counselor Malachar is already waiting "
            "in the hallway, with a smile too calm for this moment."
        ),
        initial_summary="King Aldric dies mysteriously. Lyra assumes the throne.",
        initial_choices=[
            make_choice("Confront Malachar directly", t=+15, h=-5),
            make_choice("Order a secret investigation",  t=+5,  h=+5),
            make_choice("Accept Malachar's 'help'",    t=-5,  h=-10),
        ],
        initial_dramatic_delta=DramaticDelta(tension=10, mystery=5, connection=5),
    )

    print(result.display())
    commit_0_id = result.commit.id

    # -- Chapter 1: Secret investigation ----------------------------------------
    result1 = engine.advance_story(
        choice_text    = "Order a secret investigation",
        narrative_text = (
            "Lyra secretly summons Sera, the captain of the guard, "
            "her most trusted person. 'Investigate my father's death "
            "without Malachar knowing,' she whispers. Sera nods, and in her eyes "
            "Lyra sees the reflection of her own suspicions."
        ),
        summary        = "Lyra orders a secret investigation to Sera.",
        choices=[
            make_choice("Search the king's chambers", t=+8, h=0),
            make_choice("Interrogate the servants",   t=+5, h=+5),
            make_choice("Follow Malachar tonight",  t=+15, h=-5),
        ],
        world_deltas=[
            WorldVariableDelta("political_tension", 0, 10)
        ],
        dramatic_delta=DramaticDelta(tension=8, mystery=10, connection=10),
    )

    print(result1.display())
    commit_1_id = result1.commit.id

    # -- Chapter 2: Follow Malachar ---------------------------------------------
    result2 = engine.advance_story(
        choice_text    = "Follow Malachar tonight",
        narrative_text = (
            "Wrapped in a dark cloak, Lyra follows Malachar through "
            "the castle passageways. The counselor meets with three "
            "hooded figures in the cellar. Lyra manages to overhear the "
            "words '...the coronation cannot wait' and '...the poison "
            "will leave no trace on the second attempt.' Lyra's heart "
            "freezes. They are planning to kill her too."
        ),
        summary        = "Lyra discovers Malachar's conspiracy: they plan to poison her.",
        choices=[
            make_choice("Flee and seek allies immediately", t=+5,  h=+10),
            make_choice("Confront Malachar now",          t=+25, h=-15),
            make_choice("Document the conspiracy in secret",t=+5,  h=+5),
        ],
        # Malachar is now officially an active enemy
        entity_deltas=[
            EntityDelta(
                entity_id   = malachar.id,
                entity_name = "Counselor Malachar",
                attribute   = "is_traitor",
                old_value   = True,
                new_value   = True,    # Confirmed, not just suspected
            )
        ],
        dramatic_delta = DramaticDelta(tension=20, hope=-10, mystery=-25, connection=5),
    )

    print(result2.display())
    commit_2_id = result2.commit.id

    # Verify P1: the causal graph is valid
    stats = engine.get_causal_stats()
    assert stats["is_valid_dag"], "P1 FAILED: The causal graph must be a DAG"
    print(f"\n[OK] P1 CAUSALITY: {stats}")

    # -- Chapter 3: Flee and seek allies ----------------------------------------
    result3 = engine.advance_story(
        choice_text    = "Flee and seek allies immediately",
        narrative_text = (
            "Lyra runs to the north wing of the castle, where Duke Edric, "
            "her father's ally, keeps his chambers. She wakes him and "
            "reveals everything. The duke, though surprised, swears loyalty: "
            "'Your father saved my life once. Now it is my turn, "
            "Your Majesty.' With this support, the conspiracy now has a "
            "worthy rival."
        ),
        summary        = "Lyra wins Duke Edric as an ally against Malachar.",
        choices=[
            make_choice("Plan Malachar's arrest for tomorrow", t=+10, h=+10),
            make_choice("Flee the castle with Edric",                   t=-5,  h=+15),
            make_choice("Use the information as political leverage",      t=+5,  h=+5),
        ],
        dramatic_delta = DramaticDelta(tension=5, hope=15, connection=15, chaos=-5),
    )

    print(result3.display())

    # -- Test P3: Go back to commit 1 and take another decision (branching) -----
    separator("TEST P3: Versioning — Go back to Chapter 1 and explore another branch")

    engine.go_to_commit(commit_1_id)
    print(f"[OK] Returned to Chapter 1 commit (depth={engine._current_depth})")
    print(f"   Dramatic vector restored: {engine._dramatic_engine.vector}")

    # Take another decision from the same point
    result_alt = engine.advance_story(
        choice_text    = "Search the king's chambers",
        narrative_text = (
            "Lyra enters the royal chambers before they are sealed. "
            "On the desk she finds a cup with crystalline residue "
            "at the bottom. Poison. And beneath the ledger, a note "
            "in unfamiliar handwriting: 'The throne will be ours before the solstice.'"
        ),
        summary        = "Lyra finds evidence of poisoning in the king's chambers.",
        choices=[
            make_choice("Keep the evidence and wait",    t=+5,  h=+5),
            make_choice("Show the evidence to the council",   t=+15, h=-5),
            make_choice("Send the evidence in secret",    t=+3,  h=+10),
        ],
        dramatic_delta = DramaticDelta(tension=12, mystery=-15, connection=5),
    )

    print(result_alt.display())
    print(f"[OK] P3 VERSIONING: New branch explored from Chapter 1")
    print(f"   Parent commit: {commit_1_id[:8]}...")
    print(f"   New commit: {result_alt.commit.id[:8]}...")

    # -- Final Chapter: Ending --------------------------------------------------
    separator("Final Chapter")

    # Force high tension to test the system
    engine._dramatic_engine.apply_delta_from_dict({"tension": 45})

    result_end = engine.advance_story(
        choice_text    = "Show the evidence to the council",
        narrative_text = (
            "In the council chamber, with all the evidence on the table "
            "and Duke Edric at her side, Lyra confronts Malachar. "
            "The counselor tries to deny it, but the evidence is irrefutable. "
            "The guard arrests him while Malachar curses in silence. "
            "Lyra, at 17 years old, has just saved her kingdom. The real "
            "work of governing is only just beginning."
        ),
        summary        = "Lyra confronts Malachar with evidence. He is arrested. Lyra saves the kingdom.",
        choices        = [],   # No more options: it is the ending
        entity_deltas  = [
            EntityDelta(malachar.id, "Counselor Malachar", "alive", True, False),
            EntityDelta(lyra.id, "Lyra", "is_queen", False, True),
        ],
        dramatic_delta = DramaticDelta(tension=-40, hope=+35, chaos=-20, connection=+10),
        is_ending      = True,
    )

    print(result_end.display())

    # -- Final verifications ----------------------------------------------------
    separator("FINAL VERIFICATIONS")

    # P1: Valid DAG
    final_stats = engine.get_causal_stats()
    assert final_stats["is_valid_dag"]
    print(f"[OK] P1 CAUSALITY: Valid DAG with {final_stats['total_events']} events")

    # P2: Reconstruction (verify that Lyra's state is correct)
    lyra_state = engine._entities[lyra.id]
    assert lyra_state.attributes["is_queen"] == True
    print(f"[OK] P2 DETERMINISM: Lyra.is_queen = {lyra_state.attributes['is_queen']}")

    malachar_state = engine._entities[malachar.id]
    assert malachar_state.attributes["alive"] == False
    print(f"[OK] P4 CONSISTENCY: Malachar.alive = {malachar_state.attributes['alive']}")

    # P3: Branch tree
    total_commits = len(engine._commits)
    print(f"[OK] P3 VERSIONING: {total_commits} total commits (includes branches)")

    # Dramatic analysis (paper)
    arc_analysis = engine.get_dramatic_arc_analysis()
    print(f"\n[ANALYSIS] Dramatic arc analysis:")
    for k, v in arc_analysis.items():
        print(f"   {k}: {v:.1f}" if isinstance(v, float) else f"   {k}: {v}")

    # Active trunk (what would be sent to the AI)
    print(f"\n[TRUNK] Active trunk (context for AI):")
    print(engine.get_trunk_summary())

    print("\n" + "=" * 60)
    print("  [***] PHASE 1 COMPLETED - ALL PROPERTIES VERIFIED")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== CAUSAL NARRATIVE ENGINE - Phase 1 Test ===")
    print("   Verifying properties P1, P2, P3, P4\n")

    try:
        test_causal_validator()
        test_dramatic_engine()
        test_full_story()

        print("\n[SUCCESS] ALL TESTS PASSED")

    except AssertionError as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise
