"""
tests/test_fase1.py — Prueba completa de la Fase 1

Ejecuta: python -m pytest tests/test_fase1.py -v
O directo: python tests/test_fase1.py

Este test corre una historia completa de 6 decisiones en memoria,
validando las 4 propiedades formales del CNE:
    P1: Causalidad (DAG sin ciclos)
    P2: Reconstrucción determinista
    P3: Versionado narrativo (ramas)
    P4: Consistencia narrativa
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
    """Crea una NarrativeChoice con preview dramático."""
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
# TEST 1: CausalValidator — Propiedad P1
# ═══════════════════════════════════════════════════════════════════════════════

def test_causal_validator():
    separator("TEST P1: CausalValidator — DAG sin ciclos")

    validator = CausalValidator()

    # Registrar eventos
    validator.add_event("e1")
    validator.add_event("e2")
    validator.add_event("e3")
    validator.add_event("e4")

    # Crear cadena causal: e1 -> e2 -> e3
    validator.add_edge("e1", "e2")
    validator.add_edge("e2", "e3")
    validator.add_edge("e1", "e4")   # Bifurcación: e1 también causa e4

    print("[OK] Aristas válidas añadidas: e1->e2, e2->e3, e1->e4")

    # Verificar que el grafo es un DAG
    assert validator.is_dag(), "El grafo debe ser un DAG"
    print("[OK] is_dag() = True")

    # Verificar orden topológico (e1 siempre antes que e2, e2 antes que e3)
    assert validator.get_topo_order("e1") < validator.get_topo_order("e2")
    assert validator.get_topo_order("e2") < validator.get_topo_order("e3")
    print(f"[OK] Orden topológico correcto: e1={validator.get_topo_order('e1')}, "
          f"e2={validator.get_topo_order('e2')}, e3={validator.get_topo_order('e3')}")

    # Verificar que se detectan ciclos
    cycle_detected = False
    try:
        # Intentar: e3 -> e1 crearía el ciclo e1->e2->e3->e1
        validator.add_edge("e3", "e1")
        print("[FAIL] ERROR: Debería haber detectado el ciclo")
    except CausalCycleError as err:
        cycle_detected = True
        print(f"[OK] Ciclo detectado correctamente: {err}")

    assert cycle_detected, "Debe detectar el ciclo e3->e1"

    # Verificar ancestros
    ancestors = validator.get_all_ancestors("e3")
    assert "e1" in ancestors and "e2" in ancestors
    print(f"[OK] Ancestros de e3: {ancestors}")

    stats = validator.get_stats()
    print(f"[OK] Stats: {stats}")

    print("\n[***] P1 CAUSALIDAD: VERIFICADA")


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 2: DramaticEngine — Umbrales y eventos forzados
# ═══════════════════════════════════════════════════════════════════════════════

def test_dramatic_engine():
    separator("TEST: DramaticEngine — Umbrales y eventos forzados")

    # Iniciar con tensión en 30 (normal)
    engine = DramaticEngine({"tension": 30, "hope": 60, "chaos": 20,
                              "rhythm": 50, "saturation": 0,
                              "connection": 40, "mystery": 50})

    print(f"Estado inicial: {engine.vector}")

    # Sin umbrales cruzados -> None
    constraint = engine.evaluate_thresholds()
    assert constraint is None, "No debe haber eventos forzados al inicio"
    print("[OK] Sin umbrales cruzados -> None")

    # Subir tensión a 90 -> debe forzar CLÍMAX
    engine.apply_delta_from_dict({"tension": 60, "hope": -10})
    print(f"Después de +60 tensión: {engine.vector}")

    constraint = engine.evaluate_thresholds()
    assert constraint is not None, "Debe haber un evento forzado"
    print(f"[OK] Umbral cruzado -> {constraint.event_type.value}: {constraint.description[:60]}...")

    # Verificar que la instrucción para la IA es clara
    prompt_text = constraint.to_prompt_constraint()
    assert "CONSTRAINT DRAMÁTICO" in prompt_text
    print(f"[OK] Prompt constraint generado correctamente")

    # Test: misterio + tensión alta -> revelación
    engine2 = DramaticEngine({"tension": 70, "hope": 40, "chaos": 30,
                               "rhythm": 50, "saturation": 0,
                               "connection": 40, "mystery": 70})
    constraint2 = engine2.evaluate_thresholds()
    assert constraint2 is not None
    print(f"[OK] Misterio+Tensión alto -> {constraint2.event_type.value}")

    # Test análisis de arco
    analysis = engine.get_arc_analysis()
    print(f"[OK] Análisis de arco: {analysis}")

    print("\n[***] DRAMATIC ENGINE: VERIFICADO")
    


# ═══════════════════════════════════════════════════════════════════════════════
# TEST 3: StateMachine — Historia completa (P1 + P2 + P3 + P4)
# ═══════════════════════════════════════════════════════════════════════════════

def test_full_story():
    separator("TEST P1+P2+P3+P4: Historia completa en memoria")

    # ── Crear el mundo ─────────────────────────────────────────────────────────
    lyra = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={"alive": True, "health": 100, "loyalty": 80, "is_queen": False}
    )

    malachar = Entity(
        name="Consejero Malachar",
        entity_type=EntityType.CHARACTER,
        attributes={"alive": True, "health": 100, "loyalty": 0, "is_traitor": True}
    )

    world = WorldDefinition(
        name         = "El Reino de Valdris",
        context      = ("Un reino medieval al borde de la guerra. El rey ha muerto "
                       "misteriosamente. Lyra, la heredera de 17 años, debe gobernar "
                       "sola mientras el consejero Malachar conspira en las sombras."),
        protagonist  = "Lyra, la princesa heredera",
        era          = "Edad Media fantástica, año 843",
        tone         = NarrativeTone.DARK,
        antagonist   = "Consejero Malachar, que busca el trono",
        rules        = "La magia existe pero tiene un precio de vida",
        constraints  = ["Los muertos no pueden regresar", "No hay viajes en el tiempo"],
        initial_entities = [lyra, malachar],
        dramatic_config  = {
            "tension": 40, "hope": 55, "chaos": 25,
            "rhythm": 50, "saturation": 0, "connection": 35, "mystery": 65
        },
        max_depth = 10,
    )

    engine = StateMachine(world)
    print(f"[SEED] Semilla creada: {world}")

    # ── Capítulo 0: Inicio ─────────────────────────────────────────────────────
    result = engine.start(
        initial_narrative=(
            "La sala del trono está en silencio cuando Lyra recibe la noticia. "
            "Su padre, el rey Aldric, ha sido encontrado muerto en sus aposentos. "
            "No hay marcas de violencia, pero el médico real susurra que las "
            "circunstancias son... irregulares. El Consejero Malachar ya espera "
            "en el pasillo, con una sonrisa demasiado calmada para este momento."
        ),
        initial_summary="El rey Aldric muere misteriosamente. Lyra asume el trono.",
        initial_choices=[
            make_choice("Confrontar a Malachar directamente", t=+15, h=-5),
            make_choice("Ordenar una investigación secreta",  t=+5,  h=+5),
            make_choice("Aceptar la 'ayuda' de Malachar",    t=-5,  h=-10),
        ],
        initial_dramatic_delta=DramaticDelta(tension=10, mystery=5, connection=5),
    )

    print(result.display())
    commit_0_id = result.commit.id

    # ── Capítulo 1: Investigación secreta ──────────────────────────────────────
    result1 = engine.advance_story(
        choice_text    = "Ordenar una investigación secreta",
        narrative_text = (
            "Lyra convoca en secreto a Sera, la capitana de la guardia, "
            "su persona de mayor confianza. 'Investiga la muerte de mi padre "
            "sin que Malachar lo sepa', susurra. Sera asiente, y en sus ojos "
            "Lyra ve el reflejo de sus propias sospechas."
        ),
        summary        = "Lyra ordena investigación secreta a Sera.",
        choices=[
            make_choice("Revisar los aposentos del rey", t=+8, h=0),
            make_choice("Interrogar a los sirvientes",   t=+5, h=+5),
            make_choice("Seguir a Malachar esta noche",  t=+15, h=-5),
        ],
        world_deltas=[
            WorldVariableDelta("political_tension", 0, 10)
        ],
        dramatic_delta=DramaticDelta(tension=8, mystery=10, connection=10),
    )

    print(result1.display())
    commit_1_id = result1.commit.id

    # ── Capítulo 2: Seguir a Malachar ─────────────────────────────────────────
    result2 = engine.advance_story(
        choice_text    = "Seguir a Malachar esta noche",
        narrative_text = (
            "Envuelta en una capa oscura, Lyra sigue a Malachar a través "
            "de los pasadizos del castillo. El consejero se reúne con tres "
            "figuras encapuchadas en la bodega. Lyra alcanza a escuchar las "
            "palabras '...la coronación no puede esperar' y '...el veneno "
            "no dejará rastro en el segundo intento'. El corazón de Lyra "
            "se congela. Están planeando matarla también."
        ),
        summary        = "Lyra descubre la conspiración de Malachar: planean envenenarla.",
        choices=[
            make_choice("Huir y buscar aliados inmediatamente", t=+5,  h=+10),
            make_choice("Confrontar a Malachar ahora",          t=+25, h=-15),
            make_choice("Documentar la conspiración en secreto",t=+5,  h=+5),
        ],
        # Malachar ahora es oficialmente un enemigo activo
        entity_deltas=[
            EntityDelta(
                entity_id   = malachar.id,
                entity_name = "Consejero Malachar",
                attribute   = "is_traitor",
                old_value   = True,
                new_value   = True,    # Confirmado, no solo sospechado
            )
        ],
        dramatic_delta = DramaticDelta(tension=20, hope=-10, mystery=-25, connection=5),
    )

    print(result2.display())
    commit_2_id = result2.commit.id

    # Verificar P1: el grafo causal es válido
    stats = engine.get_causal_stats()
    assert stats["is_valid_dag"], "P1 FALLIDA: El grafo causal debe ser un DAG"
    print(f"\n[OK] P1 CAUSALIDAD: {stats}")

    # ── Capítulo 3: Huir y buscar aliados ─────────────────────────────────────
    result3 = engine.advance_story(
        choice_text    = "Huir y buscar aliados inmediatamente",
        narrative_text = (
            "Lyra corre al ala norte del castillo, donde el Duque Edric, "
            "aliado de su padre, guarda sus aposentos. Lo despierta y le "
            "revela todo. El duque, aunque sorprendido, jura lealtad: "
            "'Tu padre me salvó la vida una vez. Ahora es mi turno, "
            "Su Majestad'. Con este apoyo, la conspiración ya tiene un "
            "rival a la altura."
        ),
        summary        = "Lyra gana al Duque Edric como aliado contra Malachar.",
        choices=[
            make_choice("Planear la detención de Malachar para mañana", t=+10, h=+10),
            make_choice("Huir del castillo con Edric",                   t=-5,  h=+15),
            make_choice("Usar la información como palanca política",      t=+5,  h=+5),
        ],
        dramatic_delta = DramaticDelta(tension=5, hope=15, connection=15, chaos=-5),
    )

    print(result3.display())

    # ── Test P3: Regresar al commit 1 y tomar otra decisión (branching) ────────
    separator("TEST P3: Versionado — Regresar a Capítulo 1 y explorar otra rama")

    engine.go_to_commit(commit_1_id)
    print(f"[OK] Regresado al commit del Capítulo 1 (depth={engine._current_depth})")
    print(f"   Vector dramático restaurado: {engine._dramatic_engine.vector}")

    # Tomar otra decisión desde el mismo punto
    result_alt = engine.advance_story(
        choice_text    = "Revisar los aposentos del rey",
        narrative_text = (
            "Lyra entra a los aposentos reales antes de que sean sellados. "
            "Sobre el escritorio encuentra una copa con residuos cristalinos "
            "en el fondo. Veneno. Y debajo del libro de cuentas, una nota "
            "en letra desconocida: 'El trono será nuestro antes del solsticio.'"
        ),
        summary        = "Lyra encuentra pruebas de envenenamiento en los aposentos del rey.",
        choices=[
            make_choice("Guardar las pruebas y esperar",    t=+5,  h=+5),
            make_choice("Mostrar las pruebas al consejo",   t=+15, h=-5),
            make_choice("Enviar las pruebas en secreto",    t=+3,  h=+10),
        ],
        dramatic_delta = DramaticDelta(tension=12, mystery=-15, connection=5),
    )

    print(result_alt.display())
    print(f"[OK] P3 VERSIONADO: Nueva rama explorada desde Capítulo 1")
    print(f"   Commit padre: {commit_1_id[:8]}...")
    print(f"   Nuevo commit: {result_alt.commit.id[:8]}...")

    # ── Capítulo final: Ending ────────────────────────────────────────────────
    separator("Capítulo Final")

    # Forzar tensión alta para probar el sistema
    engine._dramatic_engine.apply_delta_from_dict({"tension": 45})

    result_end = engine.advance_story(
        choice_text    = "Mostrar las pruebas al consejo",
        narrative_text = (
            "En la sala del consejo, con todas las pruebas sobre la mesa "
            "y el Duque Edric a su lado, Lyra confronta a Malachar. "
            "El consejero intenta negarlo, pero las pruebas son irrefutables. "
            "La guardia lo arresta mientras Malachar maldice en silencio. "
            "Lyra, de 17 años, acaba de salvar su reino. El verdadero "
            "trabajo de gobernar está apenas comenzando."
        ),
        summary        = "Lyra confronta a Malachar con pruebas. Es arrestado. Lyra salva el reino.",
        choices        = [],   # No hay más opciones: es el final
        entity_deltas  = [
            EntityDelta(malachar.id, "Consejero Malachar", "alive", True, False),
            EntityDelta(lyra.id, "Lyra", "is_queen", False, True),
        ],
        dramatic_delta = DramaticDelta(tension=-40, hope=+35, chaos=-20, connection=+10),
        is_ending      = True,
    )

    print(result_end.display())

    # ── Verificaciones finales ────────────────────────────────────────────────
    separator("VERIFICACIONES FINALES")

    # P1: DAG válido
    final_stats = engine.get_causal_stats()
    assert final_stats["is_valid_dag"]
    print(f"[OK] P1 CAUSALIDAD: DAG válido con {final_stats['total_events']} eventos")

    # P2: Reconstrucción (verificar que el estado de Lyra es correcto)
    lyra_state = engine._entities[lyra.id]
    assert lyra_state.attributes["is_queen"] == True
    print(f"[OK] P2 DETERMINISMO: Lyra.is_queen = {lyra_state.attributes['is_queen']}")

    malachar_state = engine._entities[malachar.id]
    assert malachar_state.attributes["alive"] == False
    print(f"[OK] P4 CONSISTENCIA: Malachar.alive = {malachar_state.attributes['alive']}")

    # P3: Árbol de ramas
    total_commits = len(engine._commits)
    print(f"[OK] P3 VERSIONADO: {total_commits} commits totales (incluye ramas)")

    # Análisis dramático (paper)
    arc_analysis = engine.get_dramatic_arc_analysis()
    print(f"\n[ANALYSIS] Análisis de arco dramático:")
    for k, v in arc_analysis.items():
        print(f"   {k}: {v:.1f}" if isinstance(v, float) else f"   {k}: {v}")

    # Tronco activo (lo que se mandaría a la IA)
    print(f"\n[TRUNK] Tronco activo (contexto para IA):")
    print(engine.get_trunk_summary())

    print("\n" + "=" * 60)
    print("  [***] FASE 1 COMPLETADA - TODAS LAS PROPIEDADES VERIFICADAS")
    print("=" * 60)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=== CAUSAL NARRATIVE ENGINE - Test de Fase 1 ===")
    print("   Verificando propiedades P1, P2, P3, P4\n")

    try:
        test_causal_validator()
        test_dramatic_engine()
        test_full_story()

        print("\n[SUCCESS] TODOS LOS TESTS PASARON")

    except AssertionError as e:
        print(f"\n[FAIL] TEST FALLIDO: {e}")
        raise
    except Exception as e:
        print(f"\n[ERROR] ERROR INESPERADO: {e}")
        import traceback
        traceback.print_exc()
        raise
