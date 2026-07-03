"""
interfaces/repository.py — Persistence contract

Defines what operations any persistence system connected to the CNE
must support. The Core Engine only knows this interface, not
the concrete implementations.

Implementations included in the repo:
- InMemoryRepository (Phase 1, tests without dependencies)
- PostgreSQLRepository (Phase 2, production)
- SQLiteRepository (Phase 2, local development)
"""

from abc import ABC, abstractmethod
from typing import Any

from cne_core.models.world import WorldDefinition, Entity
from cne_core.models.event import NarrativeEvent, CausalEdge
from cne_core.models.commit import NarrativeCommit, NarrativeChoice, Branch


class NarrativeRepository(ABC):
    """
    Abstract interface for narrative engine persistence.

    All operations are async because real implementations
    (PostgreSQL, SQLite) require it. The InMemory implementation
    is also async for interface compatibility.

    Principle: the Core Engine must not know persistence details.
    It only calls these methods. The implementation can use PostgreSQL,
    MongoDB, JSON files, or anything else.
    """

    # ── WorldDefinition ────────────────────────────────────────────────────────

    @abstractmethod
    async def save_world(self, world: WorldDefinition) -> None:
        """Persists a WorldDefinition (the seed)."""
        pass

    @abstractmethod
    async def get_world(self, world_id: str) -> WorldDefinition | None:
        """Retrieves a WorldDefinition by ID."""
        pass

    @abstractmethod
    async def list_worlds(self, limit: int = 50) -> list[WorldDefinition]:
        """Lists created worlds (for UI selection)."""
        pass

    @abstractmethod
    async def delete_world(self, world_id: str) -> bool:
        """Deletes a world and all its associated data (cascade). Returns True if it existed."""
        pass

    # ── NarrativeCommit ────────────────────────────────────────────────────────

    @abstractmethod
    async def save_commit(self, commit: NarrativeCommit) -> None:
        """
        Persists a narrative commit.

        Must be an atomic transaction: if it fails, nothing is persisted.
        In PostgreSQL this is handled with BEGIN/COMMIT.
        """
        pass

    @abstractmethod
    async def get_commit(self, commit_id: str) -> NarrativeCommit | None:
        """Retrieves a commit by ID."""
        pass

    @abstractmethod
    async def get_trunk(
        self,
        commit_id: str,
        max_depth: int = 100
    ) -> list[NarrativeCommit]:
        """
        Retrieves the chain of commits from commit_id backwards.

        Returns in chronological order (from oldest to most recent).
        If max_depth > 0, limits how many commits to retrieve.

        Args:
            commit_id: The commit to start from.
            max_depth: Maximum number of commits to return.

        Returns:
            List of commits in chronological order.
        """
        pass

    @abstractmethod
    async def list_commits(self, world_id: str) -> list[NarrativeCommit]:
        """Lists all commits for a world, ordered by depth ascending."""
        pass

    @abstractmethod
    async def get_children_commits(self, commit_id: str) -> list[NarrativeCommit]:
        """
        Returns the child commits of a given commit.

        Useful for navigating alternative branches.
        """
        pass

    # ── NarrativeEvent ─────────────────────────────────────────────────────────

    @abstractmethod
    async def save_event(self, event: NarrativeEvent) -> None:
        """Persists a narrative event."""
        pass

    @abstractmethod
    async def get_event(self, event_id: str) -> NarrativeEvent | None:
        """Retrieves an event by ID."""
        pass

    @abstractmethod
    async def get_events_for_commit(self, commit_id: str) -> list[NarrativeEvent]:
        """Returns all events associated with a commit."""
        pass

    @abstractmethod
    async def get_latest_commit_id(self, world_id: str) -> str | None:
        """Returns the ID of the most recent commit for a world, or None if there are none."""
        pass

    # ── Choices ────────────────────────────────────────────────────────────────

    @abstractmethod
    async def save_choices(self, commit_id: str, choices: list[NarrativeChoice]) -> None:
        """Persists the available choices for a commit."""
        pass

    @abstractmethod
    async def get_choices(self, commit_id: str) -> list[NarrativeChoice]:
        """Retrieves the available choices for a commit."""
        pass

    # ── Causal Graph ───────────────────────────────────────────────────────────

    @abstractmethod
    async def save_causal_edge(self, edge: CausalEdge) -> None:
        """Persists an edge of the causal graph."""
        pass

    @abstractmethod
    async def check_causal_path_exists(
        self,
        from_event_id: str,
        to_event_id: str
    ) -> bool:
        """
        Checks if a causal path exists from from_event_id to to_event_id.

        Typical implementation: recursive CTE in SQL.

        This is what prevents cycles in the DAG:
        Before inserting A->B, we verify that B->...->A does NOT exist.
        """
        pass

    @abstractmethod
    async def get_causal_parents(self, event_id: str) -> list[str]:
        """Returns the IDs of events that caused this event."""
        pass

    @abstractmethod
    async def get_causal_children(self, event_id: str) -> list[str]:
        """Returns the IDs of events caused by this event."""
        pass

    # ── Dramatic State ─────────────────────────────────────────────────────────

    @abstractmethod
    async def save_dramatic_state(
        self,
        commit_id: str,
        vector: dict[str, int],
        forced_event: str | None = None,
        trigger_meter: str | None = None
    ) -> None:
        """
        Persists the dramatic vector state at a commit.

        Args:
            commit_id: Which commit this state corresponds to.
            vector: The 7 meters (tension, hope, chaos, etc.).
            forced_event: Type of forced event if there was one.
            trigger_meter: Which meter triggered the forced event.
        """
        pass

    @abstractmethod
    async def get_dramatic_state(self, commit_id: str) -> dict[str, int] | None:
        """Retrieves the dramatic vector for a commit."""
        pass

    @abstractmethod
    async def get_forced_event_type(self, commit_id: str) -> str | None:
        """Retrieves the forced event type for a commit (if it exists)."""
        pass

    @abstractmethod
    async def save_dramatic_delta(
        self,
        event_id: str,
        meter: str,
        delta: int,
        reason: str | None = None
    ) -> None:
        """
        Persists an individual change in a dramatic meter.

        This is used for the paper: it allows analyzing which events
        affect each meter the most.

        Args:
            event_id: Event that caused the change.
            meter: Name of the meter ("tension", "hope", etc.).
            delta: Change in value (+15, -8, etc.).
            reason: Optional explanation of the change.
        """
        pass

    # ── Entity CRUD ───────────────────────────────────────────────────────────

    @abstractmethod
    async def save_entity(self, entity: Entity, world_id: str) -> None:
        """
        Persists a new entity created during the story.

        Args:
            entity: The entity to persist.
            world_id: The world it belongs to.
        """
        pass

    # ── Entity State ───────────────────────────────────────────────────────────

    @abstractmethod
    async def get_entity_state(
        self,
        entity_id: str,
        at_commit: str
    ) -> dict[str, Any] | None:
        """
        Retrieves the state of an entity at a given commit.

        In Phase 2, this will use the StateRebuilder:
        1. Finds the nearest snapshot before at_commit
        2. Applies all deltas from there to at_commit

        In Phase 1, the commit snapshot is used directly.
        """
        pass

    @abstractmethod
    async def save_entity_snapshot(
        self,
        commit_id: str,
        entity_states: dict[str, Any]
    ) -> None:
        """
        Saves a complete snapshot of all entity states.

        Done periodically (e.g., every 10 commits) to optimize
        state reconstruction.
        """
        pass

    # ── Branches ───────────────────────────────────────────────────────────────

    @abstractmethod
    async def save_branch(self, branch: Branch) -> None:
        """Persists branch metadata."""
        pass

    @abstractmethod
    async def get_branch(self, branch_id: str) -> Branch | None:
        """Retrieves branch metadata."""
        pass

    @abstractmethod
    async def list_branches(self, world_id: str) -> list[Branch]:
        """Lists all branches for a world."""
        pass

    # ── Stats ─────────────────────────────────────────────────────────────────

    @abstractmethod
    async def count_commits(self, world_id: str) -> int:
        """Counts the total commits for a world."""
        pass

    @abstractmethod
    async def count_all_commits(self) -> int:
        """Counts the total commits across all worlds."""
        pass

    @abstractmethod
    async def count_worlds(self) -> int:
        """Counts the total number of worlds."""
        pass

    @abstractmethod
    async def count_events(self) -> int:
        """Counts the total number of events."""
        pass

    # ── State Snapshots ────────────────────────────────────────────────────────

    @abstractmethod
    async def get_nearest_snapshot(
        self,
        commit_id: str
    ) -> tuple[str, dict[str, Any]] | None:
        """
        Finds the nearest snapshot before commit_id.

        Returns: (snapshot_commit_id, entity_states)

        Used by StateRebuilder to efficiently reconstruct state.
        """
        pass

    @abstractmethod
    async def get_deltas_since(
        self,
        from_commit_id: str,
        to_commit_id: str
    ) -> list[tuple[str, Any]]:
        """
        Retrieves all deltas applied between two commits.

        Returns list of (event_id, deltas) in topological order.

        Used by StateRebuilder.
        """
        pass
