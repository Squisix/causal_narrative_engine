"""
engine/causal_validator.py — El guardián de la causalidad

Esta es la pieza más importante del motor desde el punto de vista
formal. Garantiza que el grafo de eventos sea siempre un DAG
(Directed Acyclic Graph — Grafo Dirigido Acíclico).

¿Por qué importa?
- Sin esto, un evento podría ser su propia causa: A → B → A
- Eso crearía paradojas narrativas (el rey muere porque murió)
- El motor perdería la propiedad de reconstrucción determinista

Algoritmo: DFS (Depth-First Search) para detectar ciclos.
Si al añadir la arista A→B ya existe un camino B→...→A,
la arista se rechaza y se lanza CausalCycleError.

Complejidad: O(V + E) donde V = eventos, E = aristas causales.
Para historias típicas (< 1000 eventos), esto es instantáneo.
"""

from collections import defaultdict, deque
from cne_core.models.event import CausalEdge, CausalRelationType


# ── Excepciones ───────────────────────────────────────────────────────────────

class CausalCycleError(Exception):
    """
    Se lanza cuando intentar añadir una arista crearía un ciclo.
    Incluye el camino del ciclo para facilitar el debugging.
    """
    def __init__(self, cause_id: str, effect_id: str, cycle_path: list[str]):
        self.cause_id  = cause_id
        self.effect_id = effect_id
        self.cycle_path = cycle_path
        path_str = " → ".join(p[:8] + "..." for p in cycle_path)
        super().__init__(
            f"Ciclo causal detectado: añadir {cause_id[:8]}→{effect_id[:8]} "
            f"crearía el ciclo: {path_str}"
        )


class EventNotFoundError(Exception):
    """Se lanza cuando se referencia un evento que no existe en el grafo."""
    pass


# ── CausalValidator ───────────────────────────────────────────────────────────

class CausalValidator:
    """
    Mantiene el grafo causal y valida su propiedad DAG.

    El grafo se almacena en memoria como lista de adyacencia.
    En la Fase 2, esto se reemplazará por consultas a PostgreSQL,
    pero la interface permanece igual gracias al Repository pattern.

    Uso típico:
        validator = CausalValidator()
        validator.add_event("evento-1")
        validator.add_event("evento-2")
        validator.add_edge("evento-1", "evento-2")  # OK
        validator.add_edge("evento-2", "evento-1")  # → CausalCycleError!
    """

    def __init__(self):
        # Lista de adyacencia: event_id → lista de IDs de eventos causados
        # defaultdict(list) retorna [] automáticamente para claves nuevas
        self._adjacency: dict[str, list[str]] = defaultdict(list)

        # Set de todos los eventos conocidos
        self._events: set[str] = set()

        # Lista de aristas para persistencia y análisis
        self._edges: list[CausalEdge] = []

        # Orden topológico asignado a cada evento
        self._topo_order: dict[str, int] = {}
        self._next_topo: int = 0

    # ── Gestión de eventos ────────────────────────────────────────────────────

    def add_event(self, event_id: str) -> int:
        """
        Registra un nuevo evento en el grafo.

        Retorna el topo_order asignado. Este número siempre será
        mayor que el de todos sus futuros padres causales.

        Returns:
            int: El orden topológico asignado al evento.
        """
        if event_id not in self._events:
            self._events.add(event_id)
            self._topo_order[event_id] = self._next_topo
            self._next_topo += 1
        return self._topo_order[event_id]

    def event_exists(self, event_id: str) -> bool:
        return event_id in self._events

    # ── Gestión de aristas ────────────────────────────────────────────────────

    def add_edge(
        self,
        cause_id:  str,
        effect_id: str,
        relation:  CausalRelationType = CausalRelationType.DIRECT,
        strength:  float = 1.0,
    ) -> CausalEdge:
        """
        Añade una arista causal cause → effect al grafo.

        Antes de añadirla, verifica que no crea un ciclo usando DFS.
        Si hay ciclo, lanza CausalCycleError con la ruta del ciclo.

        Args:
            cause_id:  ID del evento que causa.
            effect_id: ID del evento causado.
            relation:  Tipo de relación causal.
            strength:  Intensidad de la relación [0.0 - 1.0].

        Returns:
            CausalEdge: La arista creada.

        Raises:
            EventNotFoundError: Si algún evento no está registrado.
            CausalCycleError:   Si la arista crearía un ciclo.
        """
        # Validar que ambos eventos existen
        for eid in (cause_id, effect_id):
            if not self.event_exists(eid):
                raise EventNotFoundError(
                    f"Evento {eid[:8]}... no registrado en el grafo causal. "
                    f"Llama add_event() primero."
                )

        # Verificar que la arista no ya existe
        if effect_id in self._adjacency[cause_id]:
            # Arista duplicada: la ignoramos silenciosamente
            return self._get_existing_edge(cause_id, effect_id)

        # ── PUNTO CRÍTICO: detección de ciclos ────────────────────────────────
        # Pregunta: ¿existe ya un camino de effect_id → cause_id?
        # Si sí, añadir cause_id → effect_id crearía un ciclo.
        cycle_path = self._find_path(effect_id, cause_id)
        if cycle_path is not None:
            raise CausalCycleError(cause_id, effect_id, cycle_path)
        # ─────────────────────────────────────────────────────────────────────

        # Si llegamos aquí, la arista es segura
        self._adjacency[cause_id].append(effect_id)

        edge = CausalEdge(
            cause_event_id=cause_id,
            effect_event_id=effect_id,
            relation_type=relation,
            strength=strength,
        )
        self._edges.append(edge)

        # Actualizar topo_order del efecto si es necesario
        # El efecto debe tener topo_order > que su causa
        cause_order  = self._topo_order.get(cause_id, 0)
        effect_order = self._topo_order.get(effect_id, 0)
        if effect_order <= cause_order:
            self._topo_order[effect_id] = cause_order + 1

        return edge

    # ── Queries del grafo ─────────────────────────────────────────────────────

    def get_causes(self, event_id: str) -> list[str]:
        """¿Qué eventos causaron este evento? (aristas entrantes)"""
        return [
            edge.cause_event_id
            for edge in self._edges
            if edge.effect_event_id == event_id
        ]

    def get_effects(self, event_id: str) -> list[str]:
        """¿Qué eventos fueron causados por este evento? (aristas salientes)"""
        return self._adjacency.get(event_id, []).copy()

    def get_all_ancestors(self, event_id: str) -> set[str]:
        """
        Retorna todos los ancestros causales de un evento.
        Útil para verificar coherencia: si el ancestro X ocurrió,
        todas las precondiciones de event_id están satisfechas.
        """
        ancestors: set[str] = set()
        queue = deque(self.get_causes(event_id))

        while queue:
            ancestor_id = queue.popleft()
            if ancestor_id not in ancestors:
                ancestors.add(ancestor_id)
                queue.extend(self.get_causes(ancestor_id))

        return ancestors

    def get_topo_order(self, event_id: str) -> int:
        """Retorna el orden topológico asignado al evento."""
        return self._topo_order.get(event_id, -1)

    def is_dag(self) -> bool:
        """
        Verifica que el grafo completo sea un DAG.
        Útil para tests y para el paper (demostración formal).
        Usa coloración de nodos: blanco→gris→negro.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {eid: WHITE for eid in self._events}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in self._adjacency.get(node, []):
                if color[neighbor] == GRAY:
                    return False   # ciclo detectado
                if color[neighbor] == WHITE:
                    if not dfs(neighbor):
                        return False
            color[node] = BLACK
            return True

        return all(
            dfs(node)
            for node in self._events
            if color[node] == WHITE
        )

    # ── Stats para el paper ───────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Estadísticas del grafo para métricas del paper."""
        return {
            "total_events": len(self._events),
            "total_edges":  len(self._edges),
            "root_events":  sum(1 for e in self._events if not self.get_causes(e)),
            "leaf_events":  sum(1 for e in self._events if not self.get_effects(e)),
            "is_valid_dag": self.is_dag(),
            "avg_in_degree": (
                len(self._edges) / len(self._events)
                if self._events else 0
            ),
        }

    # ── Helpers privados ──────────────────────────────────────────────────────

    def _find_path(self, start: str, target: str) -> list[str] | None:
        """
        BFS para encontrar si existe un camino de start → target.

        Si existe, retorna la ruta (para mostrar en el error).
        Si no existe, retorna None.

        Usamos BFS (Breadth-First Search) porque retorna el camino
        más corto, lo que hace el mensaje de error más legible.
        """
        if start == target:
            return [start]

        # queue contiene (nodo_actual, camino_hasta_aquí)
        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])
        visited: set[str] = {start}

        while queue:
            current, path = queue.popleft()

            for neighbor in self._adjacency.get(current, []):
                if neighbor == target:
                    return path + [neighbor]   # ¡Encontrado!

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None   # No hay camino

    def _get_existing_edge(self, cause_id: str, effect_id: str) -> CausalEdge:
        """Recupera una arista existente."""
        for edge in self._edges:
            if edge.cause_event_id == cause_id and edge.effect_event_id == effect_id:
                return edge
        raise EventNotFoundError("Arista no encontrada")
