"""
engine/state_machine.py — El orquestador del motor (Fase 1: en memoria)

Este es el NarrativeRunner mínimo: recibe una decisión del jugador,
valida que sea coherente, actualiza el estado del mundo, y retorna
el nuevo estado listo para presentar al jugador.

En Fase 1: todo ocurre en memoria (listas y dicts Python).
En Fase 2: se reemplazará por llamadas a los repositorios de PostgreSQL.
En Fase 3: se añade la llamada a la IA real.

La interface pública (advance_story) NO cambia entre fases.
Eso es el poder del Repository pattern.
"""

from dataclasses import dataclass, field
from typing import Any

from cne_core.models.world import WorldDefinition, Entity
from cne_core.models.event import (
    NarrativeEvent, EventType, EntityDelta,
    WorldVariableDelta, DramaticDelta, CausalEdge
)
from cne_core.models.commit import NarrativeCommit, NarrativeChoice, Branch
from cne_core.engine.causal_validator import CausalValidator, CausalCycleError
from cne_core.engine.dramatic_engine import DramaticEngine, ForcedEventConstraint


# ── Resultado de una transición ────────────────────────────────────────────────

@dataclass
class StoryAdvanceResult:
    """
    Lo que retorna el motor después de procesar una decisión.
    Es lo que el cliente (API, Flutter, prototipo HTML) recibe.
    """
    commit:            NarrativeCommit
    narrative_text:    str
    available_choices: list[NarrativeChoice]
    dramatic_state:    dict[str, int]
    forced_event:      ForcedEventConstraint | None = None
    is_ending:         bool = False

    def display(self) -> str:
        """Representación para terminal (útil durante desarrollo)."""
        lines = [
            f"\n{'═' * 60}",
            f"📖 CAPÍTULO {self.commit.depth}",
            f"{'─' * 60}",
            self.narrative_text,
            f"\n{'─' * 60}",
            f"🎭 Estado dramático: {self._drama_str()}",
        ]

        if self.forced_event:
            lines.append(f"⚠️  Evento forzado: {self.forced_event.event_type.value}")

        if not self.is_ending:
            lines.append(f"\n🌿 OPCIONES:")
            for i, choice in enumerate(self.available_choices, 1):
                preview = choice.get_preview_str()
                preview_str = f"  [{preview}]" if preview else ""
                lines.append(f"  {i}. {choice.text}{preview_str}")

        return "\n".join(lines)

    def _drama_str(self) -> str:
        d = self.dramatic_state
        return (
            f"T={d.get('tension',0)} "
            f"H={d.get('hope',0)} "
            f"C={d.get('chaos',0)} "
            f"M={d.get('mystery',0)}"
        )


# ── StateMachine ───────────────────────────────────────────────────────────────

class StateMachine:
    """
    El motor narrativo en su forma más básica (Fase 1).

    Gestiona:
    - El estado actual del mundo (en memoria)
    - El grafo causal de eventos
    - El vector dramático
    - El árbol de commits (la historia versionada)

    Todo en memoria: al crear una nueva instancia, la historia empieza
    de cero. En Fase 2, el estado se persiste en PostgreSQL.
    """

    def __init__(self, world: WorldDefinition):
        self.world = world

        # Estado del mundo en memoria
        self._entities: dict[str, Entity] = {
            e.id: e for e in world.initial_entities
        }
        self._world_variables: dict[str, Any] = {}

        # Grafo causal
        self._causal_validator = CausalValidator()

        # Sistema dramático inicializado con la config de la semilla
        self._dramatic_engine = DramaticEngine(world.dramatic_config)

        # Árbol de commits (la historia versionada)
        self._commits: dict[str, NarrativeCommit] = {}
        self._current_commit_id: str | None = None
        self._events: dict[str, NarrativeEvent] = {}

        # Ramas activas
        self._branches: dict[str, Branch] = {}

        # Profundidad actual
        self._current_depth: int = 0

    # ── API pública ────────────────────────────────────────────────────────────

    def start(
        self,
        initial_narrative: str,
        initial_choices: list[NarrativeChoice],
        initial_summary: str = "La historia comienza.",
        initial_dramatic_delta: DramaticDelta | None = None,
    ) -> StoryAdvanceResult:
        """
        Inicializa la historia con el primer capítulo.

        En Fase 3, esto lo generará la IA. En Fase 1, se pasa
        manualmente para probar el motor.

        Args:
            initial_narrative: El texto del primer capítulo.
            initial_choices:   Las opciones iniciales.
            initial_summary:   Resumen para el tronco activo.
            initial_dramatic_delta: Cambios iniciales al vector.

        Returns:
            StoryAdvanceResult con el estado inicial.
        """
        # Crear evento inicial
        if initial_dramatic_delta:
            self._dramatic_engine.apply_delta(initial_dramatic_delta)

        event = NarrativeEvent(
            commit_id      = "pending",   # se actualiza abajo
            event_type     = EventType.DECISION,
            narrative_text = initial_narrative,
            summary        = initial_summary,
            dramatic_delta = initial_dramatic_delta or DramaticDelta(),
            depth          = 0,
        )
        self._causal_validator.add_event(event.id)
        event.topo_order = self._causal_validator.get_topo_order(event.id)

        # Crear commit inicial
        commit = NarrativeCommit(
            world_id       = self.world.id,
            event_id       = event.id,
            depth          = 0,
            narrative_text = initial_narrative,
            summary        = initial_summary,
            dramatic_snapshot    = self._dramatic_engine.current_state.copy(),
            world_state_snapshot = self._world_variables.copy(),
            entity_states        = self._get_entity_states(),
        )

        event.commit_id = commit.id
        self._events[event.id]    = event
        self._commits[commit.id]  = commit
        self._current_commit_id   = commit.id

        return StoryAdvanceResult(
            commit            = commit,
            narrative_text    = initial_narrative,
            available_choices = initial_choices,
            dramatic_state    = self._dramatic_engine.current_state.copy(),
        )

    def advance_story(
        self,
        choice_text:      str,
        narrative_text:   str,
        summary:          str,
        choices:          list[NarrativeChoice],
        entity_deltas:    list[EntityDelta]       | None = None,
        world_deltas:     list[WorldVariableDelta] | None = None,
        dramatic_delta:   DramaticDelta | None = None,
        is_ending:        bool = False,
    ) -> StoryAdvanceResult:
        """
        Procesa una decisión del jugador y avanza la historia.

        En Fase 1: recibe la narrativa ya generada (manual o mock).
        En Fase 3: llamará a la IA para generar narrativa, luego
                   aplica validación y persistencia.

        Args:
            choice_text:    La opción que eligió el jugador.
            narrative_text: El texto narrativo para este momento.
            summary:        Resumen de 1 oración para el tronco.
            choices:        Las próximas opciones disponibles.
            entity_deltas:  Cambios en entidades causados por este evento.
            world_deltas:   Cambios en variables globales.
            dramatic_delta: Cambios en el vector dramático.
            is_ending:      ¿Es el final de la historia?

        Returns:
            StoryAdvanceResult con el nuevo estado.

        Raises:
            RuntimeError: Si la historia no ha sido iniciada.
            ValueError:   Si la historia ya llegó a su límite de profundidad.
        """
        if self._current_commit_id is None:
            raise RuntimeError("Llama a start() antes de advance_story()")

        # Verificar límite de profundidad
        if self.world.max_depth > 0 and self._current_depth >= self.world.max_depth:
            raise ValueError(
                f"La historia alcanzó su profundidad máxima ({self.world.max_depth}). "
                f"Usa is_ending=True en el último advance_story()."
            )

        self._current_depth += 1
        current_commit = self._commits[self._current_commit_id]

        # 1. Aplicar deltas de entidades
        entity_deltas = entity_deltas or []
        self._apply_entity_deltas(entity_deltas)

        # 2. Aplicar deltas de variables globales
        world_deltas = world_deltas or []
        self._apply_world_deltas(world_deltas)

        # 3. Actualizar el vector dramático
        dramatic_delta = dramatic_delta or DramaticDelta()
        self._dramatic_engine.apply_delta(dramatic_delta)

        # 4. Evaluar si hay umbrales cruzados → evento forzado
        forced_constraint = self._dramatic_engine.evaluate_thresholds()

        # 5. Crear el evento narrativo
        event = NarrativeEvent(
            commit_id              = "pending",
            event_type             = EventType.FORCED if forced_constraint else EventType.DECISION,
            narrative_text         = narrative_text,
            summary                = summary,
            triggered_by_decision  = choice_text,
            caused_by              = [current_commit.event_id],
            entity_deltas          = entity_deltas,
            world_deltas           = world_deltas,
            dramatic_delta         = dramatic_delta,
            forced_by_meter        = (
                forced_constraint.trigger_meter if forced_constraint else None
            ),
            depth                  = self._current_depth,
        )

        # 6. Registrar en el grafo causal y validar
        self._causal_validator.add_event(event.id)
        try:
            self._causal_validator.add_edge(
                current_commit.event_id,
                event.id
            )
        except CausalCycleError as e:
            # En producción: loguear y regenerar. En Fase 1: propagar.
            raise

        event.topo_order = self._causal_validator.get_topo_order(event.id)

        # 7. Crear el nuevo commit
        new_commit = NarrativeCommit(
            world_id         = self.world.id,
            event_id         = event.id,
            depth            = self._current_depth,
            parent_id        = self._current_commit_id,
            choice_text      = choice_text,
            narrative_text   = narrative_text,
            summary          = summary,
            branch_id        = current_commit.branch_id,
            is_ending        = is_ending,
            dramatic_snapshot    = self._dramatic_engine.current_state.copy(),
            world_state_snapshot = self._world_variables.copy(),
            entity_states        = self._get_entity_states(),
        )

        event.commit_id = new_commit.id

        # 8. Registrar commit y actualizar punteros
        current_commit.add_child(new_commit.id)
        self._events[event.id]       = event
        self._commits[new_commit.id] = new_commit
        self._current_commit_id      = new_commit.id

        return StoryAdvanceResult(
            commit            = new_commit,
            narrative_text    = narrative_text,
            available_choices = choices if not is_ending else [],
            dramatic_state    = self._dramatic_engine.current_state.copy(),
            forced_event      = forced_constraint,
            is_ending         = is_ending,
        )

    def go_to_commit(self, commit_id: str) -> StoryAdvanceResult:
        """
        Regresa a un commit anterior (navegación de ramas).

        Restaura el estado completo del mundo en ese punto,
        incluyendo el vector dramático.
        """
        if commit_id not in self._commits:
            raise ValueError(f"Commit {commit_id[:8]}... no existe")

        commit = self._commits[commit_id]

        # Restaurar vector dramático
        self._dramatic_engine.vector.from_dict(commit.dramatic_snapshot)

        # Restaurar variables globales
        self._world_variables = commit.world_state_snapshot.copy()

        # Restaurar entidades (simplificado para Fase 1)
        # En Fase 2 esto usará el StateRebuilder con deltas reales
        self._restore_entity_states(commit.entity_states)

        self._current_commit_id = commit_id
        self._current_depth     = commit.depth

        return StoryAdvanceResult(
            commit            = commit,
            narrative_text    = commit.narrative_text,
            available_choices = [],   # Se regenerarán en Fase 3
            dramatic_state    = commit.dramatic_snapshot.copy(),
        )

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_current_commit(self) -> NarrativeCommit | None:
        if self._current_commit_id:
            return self._commits.get(self._current_commit_id)
        return None

    def get_trunk_summary(self, max_recent: int = 6) -> str:
        """
        Construye el 'tronco activo' para enviar a la IA.

        Los commits recientes se muestran con detalle.
        Los anteriores se comprimen a 1 línea cada uno.
        """
        if not self._current_commit_id:
            return ""

        # Recopilar la cadena de commits hasta el actual
        chain: list[NarrativeCommit] = []
        cid = self._current_commit_id
        while cid:
            commit = self._commits.get(cid)
            if not commit:
                break
            chain.append(commit)
            cid = commit.parent_id

        chain.reverse()   # Orden cronológico

        lines = []
        recent_start = max(0, len(chain) - max_recent)

        # Commits viejos comprimidos
        if recent_start > 0:
            lines.append("[HISTORIA ANTERIOR COMPRIMIDA]")
            for commit in chain[:recent_start]:
                if commit.summary:
                    lines.append(commit.to_trunk_entry())

        # Commits recientes con detalle
        lines.append("\n[CAPÍTULOS RECIENTES]")
        for commit in chain[recent_start:]:
            lines.append(commit.to_trunk_entry())

        return "\n".join(lines)

    def get_causal_stats(self) -> dict:
        """Estadísticas del grafo causal (para el paper)."""
        return self._causal_validator.get_stats()

    def get_dramatic_arc_analysis(self) -> dict:
        """Análisis del arco dramático (para el paper)."""
        return self._dramatic_engine.get_arc_analysis()

    # ── Helpers privados ───────────────────────────────────────────────────────

    def _apply_entity_deltas(self, deltas: list[EntityDelta]) -> None:
        for delta in deltas:
            entity = self._entities.get(delta.entity_id)
            if entity:
                entity.attributes[delta.attribute] = delta.new_value

    def _apply_world_deltas(self, deltas: list[WorldVariableDelta]) -> None:
        for delta in deltas:
            self._world_variables[delta.variable] = delta.new_value

    def _get_entity_states(self) -> dict[str, Any]:
        """Snapshot del estado actual de todas las entidades."""
        return {
            eid: {
                "name":       e.name,
                "type":       e.entity_type.value,
                "attributes": e.attributes.copy(),
                "alive":      e.is_alive,
            }
            for eid, e in self._entities.items()
        }

    def _restore_entity_states(self, states: dict[str, Any]) -> None:
        """Restaura el estado de entidades desde un snapshot."""
        for eid, state in states.items():
            if eid in self._entities:
                self._entities[eid].attributes = state.get("attributes", {}).copy()
