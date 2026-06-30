"""
Ejemplo minimo del Causal Narrative Engine (CNE).

Usa solo el Core Engine en memoria — cero dependencias externas.
Ejecutar: python docs/examples/minimal_example.py
"""

from cne_core import (
    WorldDefinition, Entity, EntityType, NarrativeTone,
    StateMachine, NarrativeChoice, DramaticDelta,
)


def main():
    # ── 1. Crear la semilla del mundo ─────────────────────────────────────────
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
        name="Las Tierras Rotas",
        context="Un mundo postapocaliptico donde la magia resurge entre las ruinas de la civilizacion antigua.",
        protagonist="Kael, un recolector que descubre poderes magicos latentes",
        era="Post-colapso, 300 anos despues de la Gran Fractura",
        tone=NarrativeTone.MYSTERIOUS,
        antagonist="La Entidad, una fuerza antigua que despierta con la magia",
        rules="La magia consume energia vital. Cada hechizo tiene un precio.",
        constraints=[
            "Los muertos no regresan",
            "La magia no puede crear vida",
        ],
        initial_entities=[hero, mentor],
        max_depth=10,
    )

    # ── 2. Iniciar el motor ───────────────────────────────────────────────────
    engine = StateMachine(world)

    # ── 3. Capitulo 0: Inicio ─────────────────────────────────────────────────
    result = engine.start(
        initial_narrative=(
            "Entre las ruinas de lo que alguna vez fue una gran ciudad, Kael "
            "escarba buscando piezas de metal para vender en el mercado. Sus "
            "manos rozan un cristal enterrado que emite un pulso de luz azul. "
            "El cristal vibra y Kael siente una corriente de energia recorrer "
            "su cuerpo. Seraphina, la anciana que vive en la torre derruida, "
            "lo observa desde lejos con una expresion que mezcla esperanza y temor."
        ),
        initial_choices=[
            NarrativeChoice(
                text="Tocar el cristal con ambas manos",
                dramatic_preview={"tension": 10, "mystery": 15},
                tone_hint="audaz",
            ),
            NarrativeChoice(
                text="Llamar a Seraphina para que lo examine",
                dramatic_preview={"tension": 0, "connection": 10},
                tone_hint="cauteloso",
            ),
            NarrativeChoice(
                text="Enterrarlo de nuevo y alejarse",
                dramatic_preview={"tension": -5, "hope": -10},
                tone_hint="temeroso",
            ),
        ],
        initial_summary="Kael encuentra un cristal magico entre las ruinas.",
        initial_dramatic_delta=DramaticDelta(mystery=10),
    )

    print(result.display())
    print(f"\nCommit ID: {result.commit.id[:8]}...")

    # ── 4. Capitulo 1: Primera decision ───────────────────────────────────────
    result = engine.advance_story(
        choice_text="Tocar el cristal con ambas manos",
        narrative_text=(
            "Kael envuelve el cristal con ambas manos. Una explosion de luz "
            "azul ilumina las ruinas. Siente como la energia fluye hacia el, "
            "como si el cristal reconociera algo en su sangre. Imagenes "
            "fragmentadas cruzan su mente: una ciudad brillante, una guerra, "
            "una sombra inmensa que devora todo. Cuando abre los ojos, el "
            "cristal se ha fundido con su piel, dejando marcas luminosas en "
            "sus palmas. Seraphina corre hacia el. 'Lo sabia', murmura. "
            "'Eres un Portador.'"
        ),
        summary="Kael absorbe el cristal y descubre que es un Portador de magia.",
        choices=[
            NarrativeChoice(
                text="Pedir a Seraphina que le explique que es un Portador",
                dramatic_preview={"mystery": -10, "connection": 15},
                tone_hint="curioso",
            ),
            NarrativeChoice(
                text="Intentar usar la magia inmediatamente",
                dramatic_preview={"tension": 20, "chaos": 10},
                tone_hint="impulsivo",
            ),
        ],
        dramatic_delta=DramaticDelta(tension=15, hope=10, mystery=20, chaos=5),
    )

    print(result.display())

    # ── 5. Capitulo 2: Segunda decision ───────────────────────────────────────
    result = engine.advance_story(
        choice_text="Intentar usar la magia inmediatamente",
        narrative_text=(
            "Sin esperar explicaciones, Kael extiende las manos. Una onda de "
            "energia azul sale disparada, destrozando una pared cercana. El "
            "poder es embriagante pero incontrolable. Las marcas en sus palmas "
            "arden. Seraphina grita '¡Para!' pero es tarde: la explosion "
            "magica ha enviado una senal. En la distancia, algo se mueve entre "
            "las sombras. La Entidad ha sentido el despertar."
        ),
        summary="Kael libera magia sin control y alerta a la Entidad.",
        choices=[
            NarrativeChoice(
                text="Huir con Seraphina hacia las montanas",
                dramatic_preview={"tension": 5, "hope": 5},
                tone_hint="prudente",
            ),
            NarrativeChoice(
                text="Quedarse a enfrentar lo que viene",
                dramatic_preview={"tension": 25, "hope": -15},
                tone_hint="temerario",
            ),
        ],
        dramatic_delta=DramaticDelta(tension=25, hope=-10, chaos=15, mystery=10),
    )

    print(result.display())

    # ── 6. Mostrar estado del motor ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("[TRONCO ACTIVO]")
    print("=" * 60)
    print(engine.get_trunk_summary())

    print("\n" + "=" * 60)
    print("[ESTADISTICAS CAUSALES]")
    print("=" * 60)
    stats = engine.get_causal_stats()
    print(f"  Eventos totales: {stats['total_events']}")
    print(f"  Aristas causales: {stats['total_edges']}")
    print(f"  Es DAG valido: {stats['is_valid_dag']}")

    print("\n" + "=" * 60)
    print("[ARCO DRAMATICO]")
    print("=" * 60)
    arc = engine.get_dramatic_arc_analysis()
    for key, value in arc.items():
        print(f"  {key}: {value}")

    # ── 7. Demostrar viaje en el tiempo ───────────────────────────────────────
    first_commit_id = list(engine._commits.keys())[0]
    print(f"\n[VIAJE EN EL TIEMPO] Regresando al commit {first_commit_id[:8]}...")
    old_result = engine.go_to_commit(first_commit_id)
    print(f"  Depth: {old_result.commit.depth}")
    print(f"  Drama: tension={old_result.dramatic_state['tension']}, hope={old_result.dramatic_state['hope']}")


if __name__ == "__main__":
    main()
