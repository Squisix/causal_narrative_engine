"""
examples/fase2_example.py — Ejemplo completo de Fase 2

Demuestra:
- Crear un WorldDefinition
- Guardarlo en PostgreSQL
- Crear commits narrativos
- Validar grafo causal
- Navegar el trunk

Requisitos:
- PostgreSQL corriendo: `docker-compose up -d`
- Migraciones aplicadas: `alembic upgrade head`

Ejecutar:
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
    print("CNE — Ejemplo de Fase 2: Persistencia con PostgreSQL")
    print("=" * 70)

    # ── 1. Configurar DB ───────────────────────────────────────────────────────
    print("\n[1/7] Configurando base de datos...")
    db_config = DatabaseConfig(
        "postgresql+asyncpg://cne_user@localhost:5433/cne_db",
        echo=False  # echo=True para ver las queries SQL
    )
    repo = PostgreSQLRepository(db_config)
    print("[OK] Conectado a PostgreSQL")

    # ── 2. Crear WorldDefinition ──────────────────────────────────────────────
    print("\n[2/7] Creando mundo narrativo...")

    # Entidades iniciales
    hero = Entity(
        name="Lyra",
        entity_type=EntityType.CHARACTER,
        attributes={
            "health": 100,
            "courage": 85,
            "wisdom": 70,
            "alive": True,
            "role": "Guardiana del Reino"
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
            "role": "Señor Oscuro"
        }
    )

    artifact = Entity(
        name="El Cristal de la Verdad",
        entity_type=EntityType.ARTIFACT,
        attributes={
            "power_level": 100,
            "corrupted": False,
            "location": "Templo Antiguo"
        }
    )

    # WorldDefinition
    world = WorldDefinition(
        name="El Reino de las Sombras",
        context=(
            "Un reino medieval donde la magia oscura amenaza con destruir todo. "
            "El Cristal de la Verdad es la única esperanza, pero está custodiado "
            "por fuerzas antiguas que no distinguen entre el bien y el mal."
        ),
        protagonist=(
            "Lyra, una guardiana del reino que fue traicionada por aquellos "
            "a quienes juró proteger. Ahora debe decidir si salvar el reino "
            "o dejarlo caer en la oscuridad."
        ),
        era="Medieval fantástico, año 843 de la Era de los Reyes",
        tone=NarrativeTone.DARK,
        antagonist="Malachar el Corrupto, un antiguo héroe caído",
        rules="La magia oscura tiene un precio: cada hechizo corrompe el alma del usuario.",
        constraints=[
            "No hay resurrecciones — la muerte es permanente",
            "La magia tiene consecuencias irreversibles",
            "Las decisiones pasadas condicionan las opciones futuras",
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
    print(f"[OK] Mundo guardado: '{world.name}' (ID: {world.id[:8]}...)")
    print(f"   Entidades iniciales: {len(world.initial_entities)}")
    print(f"   Tono: {world.tone.value}")

    # ── 3. Crear rama principal ───────────────────────────────────────────────
    print("\n[3/7] Creando rama narrativa...")

    branch = Branch(
        world_id=world.id,
        origin_commit_id="root",  # Se actualizará cuando creemos el commit raíz
        name="Camino del Héroe",
        description="Lyra acepta su destino y enfrenta a Malachar",
    )
    await repo.save_branch(branch)
    print(f"[OK] Rama creada: '{branch.name}' (ID: {branch.id[:8]}...)")

    # ── 4. Crear commits narrativos ───────────────────────────────────────────
    print("\n[4/7] Construyendo historia...")

    # Commit 0: Inicio
    event0 = NarrativeEvent(
        commit_id="pending",
        event_type=EventType.DECISION,
        narrative_text=(
            "El reino está en peligro. Malachar ha despertado y amenaza con "
            "sumir el mundo en la oscuridad eterna. Lyra, desterrada hace años "
            "por una traición que nunca cometió, debe decidir si regresar para "
            "salvar a quienes la abandonaron."
        ),
        summary="Lyra debe decidir si regresar al reino.",
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
    print(f"   [Capítulo 0] {commit0.summary}")

    # Commit 1: Lyra decide regresar
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
            "Lyra cabalga hacia la capital. A medida que se acerca, los recuerdos "
            "de la traición vuelven a ella. Pero el deber es más fuerte que el rencor. "
            "Al llegar al palacio, descubre que el rey ha sido asesinado y Malachar "
            "ya controla gran parte del reino."
        ),
        summary="Lyra regresa y descubre que el rey ha muerto.",
        triggered_by_decision="Regresar al reino",
        caused_by=[event0.id],
        depth=1,
        dramatic_delta=DramaticDelta(tension=5, hope=-5, mystery=10),
    )

    commit1 = NarrativeCommit(
        world_id=world.id,
        event_id=event1.id,
        depth=1,
        parent_id=commit0.id,
        choice_text="Regresar al reino",
        narrative_text=event1.narrative_text,
        summary=event1.summary,
        branch_id=branch.id,
        dramatic_snapshot=dramatic_state_1,
    )

    event1.commit_id = commit1.id
    await repo.save_commit(commit1)
    await repo.save_event(event1)
    await repo.save_dramatic_state(commit1.id, dramatic_state_1)

    # Crear arista causal
    edge_0_1 = CausalEdge(
        cause_event_id=event0.id,
        effect_event_id=event1.id,
    )
    await repo.save_causal_edge(edge_0_1)
    print(f"   [Capítulo 1] {commit1.summary}")

    # Commit 2: Lyra encuentra al Cristal
    dramatic_state_2 = {
        "tension": 60,
        "hope": 55,
        "chaos": 35,
        "rhythm": 60,
        "saturation": 10,
        "connection": 40,
        "mystery": 65,
    }

    # Delta: Lyra obtiene el Cristal
    delta_crystal = EntityDelta(
        entity_id=artifact.id,
        entity_name=artifact.name,
        attribute="location",
        old_value="Templo Antiguo",
        new_value="En posesión de Lyra",
    )

    event2 = NarrativeEvent(
        commit_id="pending",
        event_type=EventType.DECISION,
        narrative_text=(
            "Tras semanas de búsqueda, Lyra encuentra el Templo Antiguo. "
            "El Cristal de la Verdad brilla con una luz propia, pero al tocarlo, "
            "siente una presencia oscura. El Cristal le muestra visiones del pasado: "
            "la traición que la desterró fue orquestada por Malachar desde las sombras."
        ),
        summary="Lyra obtiene el Cristal y descubre la verdad.",
        triggered_by_decision="Buscar el Cristal de la Verdad",
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
        choice_text="Buscar el Cristal de la Verdad",
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
    print(f"   [Capítulo 2] {commit2.summary}")

    print(f"\n[OK] Historia creada: {commit2.depth + 1} capítulos")

    # ── 5. Recuperar trunk ─────────────────────────────────────────────────────
    print("\n[5/7] Recuperando historia completa...")

    trunk = await repo.get_trunk(commit2.id, max_depth=100)
    print(f"[OK] Trunk recuperado: {len(trunk)} commits")
    for i, commit in enumerate(trunk):
        print(f"   [{i}] {commit.summary}")

    # ── 6. Validar grafo causal ────────────────────────────────────────────────
    print("\n[6/7] Validando grafo causal...")

    # Verificar que existe el camino event0 -> event1 -> event2
    path_exists = await repo.check_causal_path_exists(event0.id, event2.id)
    print(f"[OK] Camino causal event0 -> event2: {'Existe' if path_exists else 'No existe'}")

    # Intentar crear ciclo (debe fallar)
    try:
        edge_2_0 = CausalEdge(
            cause_event_id=event2.id,
            effect_event_id=event0.id,
        )
        await repo.save_causal_edge(edge_2_0)
        print("[ERROR] Se permitio crear un ciclo")
    except ValueError as e:
        print(f"[OK] Ciclo detectado correctamente: {str(e)[:60]}...")

    # ── 7. Estado dramático ────────────────────────────────────────────────────
    print("\n[7/7] Análisis dramático...")

    for i, commit in enumerate(trunk):
        state = await repo.get_dramatic_state(commit.id)
        if state:
            print(f"   [Cap.{i}] T={state['tension']:>2} H={state['hope']:>2} M={state['mystery']:>2}")

    # ── Resumen ────────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("RESUMEN DE FASE 2")
    print("=" * 70)
    print(f"[OK] Mundo persistido: {world.name}")
    print(f"[OK] Commits guardados: {len(trunk)}")
    print(f"[OK] Grafo causal validado (sin ciclos)")
    print(f"[OK] Vector dramático rastreado")
    print(f"[OK] Deltas de entidades registrados")
    print("\nPróximos pasos:")
    print("  • Fase 3: Conectar IA (Anthropic/Claude)")
    print("  • Fase 4: API REST con FastAPI")
    print("  • Fase 5: Release público + docs")
    print("=" * 70)

    # Cleanup
    await db_config.dispose()


if __name__ == "__main__":
    asyncio.run(main())
