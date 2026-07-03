"""
engine/causal_validator.py — The guardian of causality

This is the most important component of the engine from a formal standpoint.
It guarantees that the event graph is always a DAG (Directed Acyclic Graph).

Why does it matter?
- Without this, an event could be its own cause: A → B → A
- That would create narrative paradoxes (e.g., the king dies because he died)
- The engine would lose its deterministic reconstruction property

Algorithm: DFS (Depth-First Search) to detect cycles.
If adding the edge A→B already has a path B→...→A,
the edge is rejected and a CausalCycleError is raised.

Complexity: O(V + E) where V = events, E = causal edges.
For typical stories (< 1000 events), this is instantaneous.
"""

from collections import defaultdict, deque
from cne_core.models.event import CausalEdge, CausalRelationType


# ── Exceptions ────────────────────────────────────────────────────────────────

class CausalCycleError(Exception):
    """
    Raised when attempting to add an edge would create a cycle.
    Includes the cycle path to facilitate debugging.
    """
    def __init__(self, cause_id: str, effect_id: str, cycle_path: list[str]):
        self.cause_id  = cause_id
        self.effect_id = effect_id
        self.cycle_path = cycle_path
        path_str = " -> ".join(p[:8] + "..." for p in cycle_path)
        super().__init__(
            f"Causal cycle detected: adding {cause_id[:8]}->{effect_id[:8]} "
            f"would create the cycle: {path_str}"
        )


class EventNotFoundError(Exception):
    """Raised when referencing an event that does not exist in the graph."""
    pass


# ── CausalValidator ───────────────────────────────────────────────────────────

class CausalValidator:
    """
    Maintains the causal graph and validates its DAG property.

    The graph is stored in memory as an adjacency list.
    In Phase 2, this will be replaced with PostgreSQL queries,
    but the interface remains the same thanks to the Repository pattern.

    Typical usage:
        validator = CausalValidator()
        validator.add_event("event-1")
        validator.add_event("event-2")
        validator.add_edge("event-1", "event-2")  # OK
        validator.add_edge("event-2", "event-1")  # → CausalCycleError!
    """

    def __init__(self):
        # Adjacency list: event_id → list of caused event IDs
        # defaultdict(list) automatically returns [] for new keys
        self._adjacency: dict[str, list[str]] = defaultdict(list)

        # Set of all known events
        self._events: set[str] = set()

        # List of edges for persistence and analysis
        self._edges: list[CausalEdge] = []

        # Topological order assigned to each event
        self._topo_order: dict[str, int] = {}
        self._next_topo: int = 0

    # ── Event Management ──────────────────────────────────────────────────────

    def add_event(self, event_id: str) -> int:
        """
        Registers a new event in the graph.

        Returns the assigned topo_order. This number will always be
        greater than that of all its future causal parents.

        Returns:
            int: The topological order assigned to the event.
        """
        if event_id not in self._events:
            self._events.add(event_id)
            self._topo_order[event_id] = self._next_topo
            self._next_topo += 1
        return self._topo_order[event_id]

    def event_exists(self, event_id: str) -> bool:
        return event_id in self._events

    # ── Edge Management ───────────────────────────────────────────────────────

    def add_edge(
        self,
        cause_id:  str,
        effect_id: str,
        relation:  CausalRelationType = CausalRelationType.DIRECT,
        strength:  float = 1.0,
    ) -> CausalEdge:
        """
        Adds a causal edge cause → effect to the graph.

        Before adding it, verifies that it does not create a cycle using DFS.
        If a cycle is detected, raises CausalCycleError with the cycle path.

        Args:
            cause_id:  ID of the causing event.
            effect_id: ID of the caused event.
            relation:  Type of causal relation.
            strength:  Intensity of the relation [0.0 - 1.0].

        Returns:
            CausalEdge: The created edge.

        Raises:
            EventNotFoundError: If any event is not registered.
            CausalCycleError:   If the edge would create a cycle.
        """
        # Validate that both events exist
        for eid in (cause_id, effect_id):
            if not self.event_exists(eid):
                raise EventNotFoundError(
                    f"Event {eid[:8]}... not registered in the causal graph. "
                    f"Call add_event() first."
                )

        # Verify that the edge does not already exist
        if effect_id in self._adjacency[cause_id]:
            # Duplicate edge: ignore silently
            return self._get_existing_edge(cause_id, effect_id)

        # ── CRITICAL POINT: cycle detection ───────────────────────────────────
        # Question: does a path from effect_id → cause_id already exist?
        # If so, adding cause_id → effect_id would create a cycle.
        cycle_path = self._find_path(effect_id, cause_id)
        if cycle_path is not None:
            raise CausalCycleError(cause_id, effect_id, cycle_path)
        # ─────────────────────────────────────────────────────────────────────

        # If we reach here, the edge is safe
        self._adjacency[cause_id].append(effect_id)

        edge = CausalEdge(
            cause_event_id=cause_id,
            effect_event_id=effect_id,
            relation_type=relation,
            strength=strength,
        )
        self._edges.append(edge)

        # Update the effect's topo_order if necessary
        # The effect must have a topo_order > than its cause
        cause_order  = self._topo_order.get(cause_id, 0)
        effect_order = self._topo_order.get(effect_id, 0)
        if effect_order <= cause_order:
            self._topo_order[effect_id] = cause_order + 1

        return edge

    # ── Graph Queries ─────────────────────────────────────────────────────────

    def get_causes(self, event_id: str) -> list[str]:
        """Which events caused this event? (incoming edges)"""
        return [
            edge.cause_event_id
            for edge in self._edges
            if edge.effect_event_id == event_id
        ]

    def get_effects(self, event_id: str) -> list[str]:
        """Which events were caused by this event? (outgoing edges)"""
        return self._adjacency.get(event_id, []).copy()

    def get_all_ancestors(self, event_id: str) -> set[str]:
        """
        Returns all causal ancestors of an event.
        Useful for verifying consistency: if ancestor X occurred,
        all preconditions of event_id are satisfied.
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
        """Returns the topological order assigned to the event."""
        return self._topo_order.get(event_id, -1)

    def is_dag(self) -> bool:
        """
        Verifies that the complete graph is a DAG.
        Useful for tests and for the paper (formal demonstration).
        Uses node coloring: white→gray→black.
        """
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {eid: WHITE for eid in self._events}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in self._adjacency.get(node, []):
                if color[neighbor] == GRAY:
                    return False   # cycle detected
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

    # ── Paper Stats ───────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Graph statistics for paper metrics."""
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

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _find_path(self, start: str, target: str) -> list[str] | None:
        """
        BFS to find if a path exists from start → target.

        If it exists, returns the path (to display in the error).
        If it does not exist, returns None.

        We use BFS (Breadth-First Search) because it returns the shortest
        path, making the error message more readable.
        """
        if start == target:
            return [start]

        # queue contains (current_node, path_so_far)
        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])
        visited: set[str] = {start}

        while queue:
            current, path = queue.popleft()

            for neighbor in self._adjacency.get(current, []):
                if neighbor == target:
                    return path + [neighbor]   # Found!

                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))

        return None   # No path found

    def _get_existing_edge(self, cause_id: str, effect_id: str) -> CausalEdge:
        """Retrieves an existing edge."""
        for edge in self._edges:
            if edge.cause_event_id == cause_id and edge.effect_event_id == effect_id:
                return edge
        raise EventNotFoundError("Edge not found")
