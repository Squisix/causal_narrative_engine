"""
Minimal example of the Causal Narrative Engine (CNE).

Uses only the Core Engine in memory — zero external dependencies.
Run: python docs/examples/minimal_example.py
"""

from cne_core import (
    WorldDefinition, Entity, EntityType, NarrativeTone,
    StateMachine, NarrativeChoice, DramaticDelta,
)


def main():
    # -- 1. Create the world seed ----------------------------------------------
    hero = Entity(
        name="Kael",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 100, "magic": 50, "courage": 70}
    )

    mentor = Entity(
        name="Seraphina",
        entity_type=EntityType.CHARACTER,
        attributes={"health": 80, "wisdom": 95}
    )

    world = WorldDefinition(
        name="The Broken Lands",
        context="A post-apocalyptic world where magic resurges among the ruins of an ancient civilization.",
        protagonist="Kael, a scavenger who discovers latent magical powers",
        era="Post-collapse, 300 years after the Great Fracture",
        tone=NarrativeTone.MYSTERIOUS,
        antagonist="The Entity, an ancient force that awakens with the magic",
        rules="Magic consumes life energy. Every spell has a price.",
        constraints=[
            "The dead do not return",
            "Magic cannot create life",
        ],
        initial_entities=[hero, mentor],
        max_depth=10,
    )

    # -- 2. Start the engine ---------------------------------------------------
    engine = StateMachine(world)

    # -- 3. Chapter 0: Beginning -----------------------------------------------
    result = engine.start(
        initial_narrative=(
            "Among the ruins of what was once a great city, Kael "
            "scavenges for metal pieces to sell at the market. His "
            "hands brush against a buried crystal that emits a pulse of blue light. "
            "The crystal vibrates and Kael feels a current of energy coursing through "
            "his body. Seraphina, the elder who lives in the crumbling tower, "
            "watches him from afar with an expression that mixes hope and fear."
        ),
        initial_choices=[
            NarrativeChoice(
                text="Touch the crystal with both hands",
                dramatic_preview={"tension": 10, "mystery": 15},
                tone_hint="bold",
            ),
            NarrativeChoice(
                text="Call Seraphina to examine it",
                dramatic_preview={"tension": 0, "connection": 10},
                tone_hint="cautious",
            ),
            NarrativeChoice(
                text="Bury it again and walk away",
                dramatic_preview={"tension": -5, "hope": -10},
                tone_hint="fearful",
            ),
        ],
        initial_summary="Kael finds a magical crystal among the ruins.",
        initial_dramatic_delta=DramaticDelta(mystery=10),
    )

    print(result.display())
    print(f"\nCommit ID: {result.commit.id[:8]}...")

    # -- 4. Chapter 1: First decision ------------------------------------------
    result = engine.advance_story(
        choice_text="Touch the crystal with both hands",
        narrative_text=(
            "Kael wraps the crystal with both hands. An explosion of blue "
            "light illuminates the ruins. He feels energy flowing into him, "
            "as if the crystal recognized something in his blood. Fragmented "
            "images cross his mind: a brilliant city, a war, "
            "an immense shadow that devours everything. When he opens his eyes, the "
            "crystal has fused with his skin, leaving luminous marks on "
            "his palms. Seraphina runs toward him. 'I knew it,' she murmurs. "
            "'You are a Bearer.'"
        ),
        summary="Kael absorbs the crystal and discovers he is a Bearer of magic.",
        choices=[
            NarrativeChoice(
                text="Ask Seraphina to explain what a Bearer is",
                dramatic_preview={"mystery": -10, "connection": 15},
                tone_hint="curious",
            ),
            NarrativeChoice(
                text="Try to use the magic immediately",
                dramatic_preview={"tension": 20, "chaos": 10},
                tone_hint="impulsive",
            ),
        ],
        dramatic_delta=DramaticDelta(tension=15, hope=10, mystery=20, chaos=5),
    )

    print(result.display())

    # -- 5. Chapter 2: Second decision -----------------------------------------
    result = engine.advance_story(
        choice_text="Try to use the magic immediately",
        narrative_text=(
            "Without waiting for explanations, Kael extends his hands. A wave of "
            "blue energy shoots out, destroying a nearby wall. The "
            "power is intoxicating but uncontrollable. The marks on his palms "
            "burn. Seraphina shouts 'Stop!' but it is too late: the magical "
            "explosion has sent a signal. In the distance, something moves among "
            "the shadows. The Entity has sensed the awakening."
        ),
        summary="Kael unleashes uncontrolled magic and alerts the Entity.",
        choices=[
            NarrativeChoice(
                text="Flee with Seraphina toward the mountains",
                dramatic_preview={"tension": 5, "hope": 5},
                tone_hint="prudent",
            ),
            NarrativeChoice(
                text="Stay and face whatever comes",
                dramatic_preview={"tension": 25, "hope": -15},
                tone_hint="reckless",
            ),
        ],
        dramatic_delta=DramaticDelta(tension=25, hope=-10, chaos=15, mystery=10),
    )

    print(result.display())

    # -- 6. Show engine state --------------------------------------------------
    print("\n" + "=" * 60)
    print("[ACTIVE TRUNK]")
    print("=" * 60)
    print(engine.get_trunk_summary())

    print("\n" + "=" * 60)
    print("[CAUSAL STATISTICS]")
    print("=" * 60)
    stats = engine.get_causal_stats()
    print(f"  Total events: {stats['total_events']}")
    print(f"  Causal edges: {stats['total_edges']}")
    print(f"  Is valid DAG: {stats['is_valid_dag']}")

    print("\n" + "=" * 60)
    print("[DRAMATIC ARC]")
    print("=" * 60)
    arc = engine.get_dramatic_arc_analysis()
    for key, value in arc.items():
        print(f"  {key}: {value}")

    # -- 7. Demonstrate time travel --------------------------------------------
    first_commit_id = list(engine._commits.keys())[0]
    print(f"\n[TIME TRAVEL] Returning to commit {first_commit_id[:8]}...")
    old_result = engine.go_to_commit(first_commit_id)
    print(f"  Depth: {old_result.commit.depth}")
    print(f"  Drama: tension={old_result.dramatic_state['tension']}, hope={old_result.dramatic_state['hope']}")


if __name__ == "__main__":
    main()
