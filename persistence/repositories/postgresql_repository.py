"""
persistence/repositories/postgresql_repository.py

Concrete implementation of NarrativeRepository for PostgreSQL.

Converts between:
- Core dataclasses (WorldDefinition, NarrativeEvent, etc.)
- SQLAlchemy ORM models (WorldORM, EventORM, etc.)
"""

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Any, List
import uuid

from cne_core.interfaces.repository import NarrativeRepository
from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone
from cne_core.models.event import (
    NarrativeEvent, CausalEdge, EventType, EntityDelta,
    WorldVariableDelta, DramaticDelta, CausalRelationType
)
from cne_core.models.commit import NarrativeCommit, NarrativeChoice, Branch

from persistence.database import DatabaseConfig
from persistence.models.world_orm import WorldORM, EntityORM
from persistence.models.event_orm import (
    EventORM, CausalEdgeORM, EntityDeltaORM, EntityCreationORM, WorldVariableDeltaORM
)
from persistence.models.commit_orm import CommitORM, BranchORM, DramaticStateORM, DramaticDeltaORM, ChoiceORM
from persistence.queries.causal_queries import CausalGraphQueries


class PostgreSQLRepository(NarrativeRepository):
    """
    PostgreSQL implementation of NarrativeRepository.

    Uses SQLAlchemy 2.0 async for all operations.
    """

    def __init__(self, session: AsyncSession):
        """
        Args:
            session: SQLAlchemy async session (injected by FastAPI).
        """
        self.session = session

    # ── WorldDefinition ────────────────────────────────────────────────────────

    async def save_world(self, world: WorldDefinition) -> None:
        # Convert WorldDefinition to WorldORM
        world_orm = WorldORM(
            id=world.id,
            name=world.name,
            context=world.context,
            protagonist=world.protagonist,
            era=world.era,
            tone=world.tone.value,
            antagonist=world.antagonist,
            rules=world.rules,
            constraints=world.constraints,
            dramatic_config=world.dramatic_config,
            max_depth=world.max_depth,
            output_language=world.output_language,
            created_at=world.created_at,
        )

        # Convert initial entities
        for entity in world.initial_entities:
            entity_orm = EntityORM(
                id=entity.id,
                world_id=world.id,
                name=entity.name,
                entity_type=entity.entity_type.value,
                attributes=entity.attributes,
                created_at_depth=entity.created_at_depth,
                destroyed_at_depth=entity.destroyed_at_depth,
            )
            self.session.add(entity_orm)

        self.session.add(world_orm)
        # Flush to ensure data is written before returning
        await self.session.flush()
        # Commit is handled automatically by get_session() on completion

    async def get_world(self, world_id: str) -> WorldDefinition | None:
        result = await self.session.execute(
            select(WorldORM)
            .options(selectinload(WorldORM.entities))
            .where(WorldORM.id == world_id)
        )
        world_orm = result.scalar_one_or_none()

        if world_orm is None:
            return None

        # Convert ORM → Dataclass
        return self._world_orm_to_dataclass(world_orm)

    async def delete_world(self, world_id: str) -> bool:
        result = await self.session.execute(
            select(WorldORM).where(WorldORM.id == world_id)
        )
        world_orm = result.scalar_one_or_none()
        if world_orm is None:
            return False

        await self.session.delete(world_orm)
        await self.session.flush()
        return True

    async def list_worlds(self, limit: int = 50) -> list[WorldDefinition]:
        result = await self.session.execute(
            select(WorldORM)
            .options(selectinload(WorldORM.entities))
            .order_by(WorldORM.created_at.desc())
            .limit(limit)
        )
        worlds_orm = result.scalars().all()

        return [self._world_orm_to_dataclass(w) for w in worlds_orm]

    # ── NarrativeCommit ────────────────────────────────────────────────────────

    async def save_commit(self, commit: NarrativeCommit) -> None:
        commit_orm = CommitORM(
            id=commit.id,
            world_id=commit.world_id,
            branch_id=commit.branch_id,
            parent_id=commit.parent_id,
            choice_text=commit.choice_text,
            narrative_text=commit.narrative_text,
            summary=commit.summary,
            depth=commit.depth,
            is_ending=commit.is_ending,
            world_state_snapshot=commit.world_state_snapshot,
            entity_states_snapshot=commit.entity_states,
            created_at=commit.created_at,
        )

        self.session.add(commit_orm)
        # Commit handled by get_session() context manager

    async def get_commit(self, commit_id: str) -> NarrativeCommit | None:
        result = await self.session.execute(
            select(CommitORM)
            .options(
                selectinload(CommitORM.dramatic_state),
                selectinload(CommitORM.events),
                selectinload(CommitORM.choices),
            )
            .where(CommitORM.id == commit_id)
        )
        commit_orm = result.scalar_one_or_none()

        if commit_orm is None:
            return None

        return self._commit_orm_to_dataclass(commit_orm)

    async def get_trunk(
        self,
        commit_id: str,
        max_depth: int = 100
    ) -> list[NarrativeCommit]:
        """
        Retrieves the chain of commits from commit_id backwards.
        Returns in chronological order (oldest to most recent).
        """
        commits = []
        current_id = commit_id
        depth = 0

        while current_id and depth < max_depth:
            result = await self.session.execute(
                select(CommitORM)
                .options(
                    selectinload(CommitORM.dramatic_state),
                    selectinload(CommitORM.events),
                    selectinload(CommitORM.choices),
                )
                .where(CommitORM.id == current_id)
            )
            commit_orm = result.scalar_one_or_none()

            if commit_orm is None:
                break

            commits.append(self._commit_orm_to_dataclass(commit_orm))
            current_id = commit_orm.parent_id
            depth += 1

        # Reverse for chronological order
        commits.reverse()
        return commits

    async def list_commits(self, world_id: str) -> list[NarrativeCommit]:
        result = await self.session.execute(
            select(CommitORM)
            .options(
                selectinload(CommitORM.dramatic_state),
                selectinload(CommitORM.events),
                selectinload(CommitORM.choices),
            )
            .where(CommitORM.world_id == world_id)
            .order_by(CommitORM.depth.asc())
        )
        commits_orm = result.scalars().all()
        return [self._commit_orm_to_dataclass(c) for c in commits_orm]

    async def get_children_commits(self, commit_id: str) -> list[NarrativeCommit]:
        result = await self.session.execute(
            select(CommitORM)
            .options(
                selectinload(CommitORM.dramatic_state),
                selectinload(CommitORM.events),
                selectinload(CommitORM.choices),
            )
            .where(CommitORM.parent_id == commit_id)
        )
        commits_orm = result.scalars().all()

        return [self._commit_orm_to_dataclass(c) for c in commits_orm]

    async def get_latest_commit_id(self, world_id: str) -> str | None:
        result = await self.session.execute(
            select(CommitORM.id)
            .where(CommitORM.world_id == world_id)
            .order_by(CommitORM.depth.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Choices ────────────────────────────────────────────────────────────────

    async def save_choices(self, commit_id: str, choices: list[NarrativeChoice]) -> None:
        for i, choice in enumerate(choices):
            choice_orm = ChoiceORM(
                commit_id=commit_id,
                text=choice.text,
                tone_hint=choice.tone_hint,
                estimated_depth_until_ending=choice.estimated_depth_until_ending,
                display_order=i,
            )
            self.session.add(choice_orm)

    async def get_choices(self, commit_id: str) -> list[NarrativeChoice]:
        result = await self.session.execute(
            select(ChoiceORM)
            .where(ChoiceORM.commit_id == commit_id)
            .order_by(ChoiceORM.display_order)
        )
        choices_orm = result.scalars().all()
        return [
            NarrativeChoice(
                text=c.text,
                tone_hint=c.tone_hint or "",
                estimated_depth_until_ending=c.estimated_depth_until_ending,
            )
            for c in choices_orm
        ]

    # ── NarrativeEvent ─────────────────────────────────────────────────────────

    async def save_event(self, event: NarrativeEvent) -> None:
        event_orm = EventORM(
            id=event.id,
            commit_id=event.commit_id,
            event_type=event.event_type.value,
            narrative_text=event.narrative_text,
            summary=event.summary,
            triggered_by_decision=event.triggered_by_decision,
            causal_reason=event.causal_reason,
            forced_by_meter=event.forced_by_meter,
            depth=event.depth,
            topo_order=event.topo_order,
            created_at=event.created_at,
        )

        # Add event_orm FIRST so that deltas can reference it
        self.session.add(event_orm)
        await self.session.flush()  # Force immediate INSERT of event

        # Save entity deltas
        for delta in event.entity_deltas:
            delta_orm = EntityDeltaORM(
                event_id=event.id,
                entity_id=delta.entity_id,
                entity_name=delta.entity_name,
                attribute=delta.attribute,
                old_value=delta.old_value,
                new_value=delta.new_value,
            )
            self.session.add(delta_orm)

        # Save world deltas
        for delta in event.world_deltas:
            delta_orm = WorldVariableDeltaORM(
                event_id=event.id,
                variable=delta.variable,
                old_value=delta.old_value,
                new_value=delta.new_value,
            )
            self.session.add(delta_orm)

        # Save entity creations
        for creation in event.entity_creations:
            creation_orm = EntityCreationORM(
                event_id=event.id,
                entity_id=creation.entity_id,
                entity_name=creation.entity_name,
                entity_type=creation.entity_type,
                attributes=creation.attributes,
            )
            self.session.add(creation_orm)

        # Save dramatic deltas
        if not event.dramatic_delta.is_empty():
            for meter, value in event.dramatic_delta.to_dict().items():
                if value != 0:
                    delta_orm = DramaticDeltaORM(
                        event_id=event.id,
                        meter=meter,
                        delta=value,
                    )
                    self.session.add(delta_orm)

        # Commit handled by get_session() context manager

    async def get_event(self, event_id: str) -> NarrativeEvent | None:
        result = await self.session.execute(
            select(EventORM)
            .options(
                selectinload(EventORM.entity_deltas),
                selectinload(EventORM.world_deltas),
                selectinload(EventORM.causal_parents),
            )
            .where(EventORM.id == event_id)
        )
        event_orm = result.scalar_one_or_none()

        if event_orm is None:
            return None

        return await self._event_orm_to_dataclass(self.session, event_orm)

    async def get_events_for_commit(self, commit_id: str) -> list[NarrativeEvent]:
        result = await self.session.execute(
            select(EventORM)
            .options(
                selectinload(EventORM.entity_deltas),
                selectinload(EventORM.world_deltas),
                selectinload(EventORM.causal_parents),
            )
            .where(EventORM.commit_id == commit_id)
        )
        events_orm = result.scalars().all()

        return [await self._event_orm_to_dataclass(self.session, e) for e in events_orm]

    # ── Causal Graph ───────────────────────────────────────────────────────────

    async def save_causal_edge(self, edge: CausalEdge) -> None:
        # FIRST: verify that no cycle would be created
        path_exists = await CausalGraphQueries.check_causal_path_exists(
            self.session,
            edge.effect_event_id,  # From the effect
            edge.cause_event_id    # Towards the cause
        )

        if path_exists:
            raise ValueError(
                f"Cannot create edge {edge.cause_event_id[:8]}... -> "
                f"{edge.effect_event_id[:8]}... because it would create a cycle."
            )

        # OK, no cycle. Save the edge.
        edge_orm = CausalEdgeORM(
            id=edge.id,
            cause_event_id=edge.cause_event_id,
            effect_event_id=edge.effect_event_id,
            relation_type=edge.relation_type.value,
            strength=edge.strength,
        )

        self.session.add(edge_orm)
        # Commit handled by get_session() context manager

    async def check_causal_path_exists(
        self,
        from_event_id: str,
        to_event_id: str
    ) -> bool:
        return await CausalGraphQueries.check_causal_path_exists(
            self.session,
            from_event_id,
            to_event_id
        )

    async def get_causal_parents(self, event_id: str) -> list[str]:
        result = await self.session.execute(
            select(CausalEdgeORM.cause_event_id)
            .where(CausalEdgeORM.effect_event_id == event_id)
        )
        return [row[0] for row in result.fetchall()]

    async def get_causal_children(self, event_id: str) -> list[str]:
        result = await self.session.execute(
            select(CausalEdgeORM.effect_event_id)
            .where(CausalEdgeORM.cause_event_id == event_id)
        )
        return [row[0] for row in result.fetchall()]

    # ── Dramatic State ─────────────────────────────────────────────────────────

    async def save_dramatic_state(
        self,
        commit_id: str,
        vector: dict[str, int],
        forced_event: str | None = None,
        trigger_meter: str | None = None
    ) -> None:
        dramatic_state = DramaticStateORM(
            id=str(uuid.uuid4()),
            commit_id=commit_id,
            tension=vector.get("tension", 30),
            hope=vector.get("hope", 60),
            chaos=vector.get("chaos", 20),
            rhythm=vector.get("rhythm", 50),
            saturation=vector.get("saturation", 0),
            connection=vector.get("connection", 40),
            mystery=vector.get("mystery", 50),
            forced_event=forced_event,
            trigger_meter=trigger_meter,
        )

        self.session.add(dramatic_state)
        # Commit handled by get_session() context manager

    async def get_dramatic_state(self, commit_id: str) -> dict[str, int] | None:
        result = await self.session.execute(
            select(DramaticStateORM)
            .where(DramaticStateORM.commit_id == commit_id)
        )
        state = result.scalar_one_or_none()

        if state is None:
            return None

        return state.to_dict()

    async def get_forced_event_type(self, commit_id: str) -> str | None:
        result = await self.session.execute(
            select(DramaticStateORM.forced_event)
            .where(DramaticStateORM.commit_id == commit_id)
        )
        return result.scalar_one_or_none()

    async def save_dramatic_delta(
        self,
        event_id: str,
        meter: str,
        delta: int,
        reason: str | None = None
    ) -> None:
        delta_orm = DramaticDeltaORM(
            event_id=event_id,
            meter=meter,
            delta=delta,
            reason=reason,
        )
        self.session.add(delta_orm)
        # Commit handled by get_session() context manager

    # ── Stats ─────────────────────────────────────────────────────────────────

    async def count_commits(self, world_id: str) -> int:
        result = await self.session.execute(
            select(func.count(CommitORM.id))
            .where(CommitORM.world_id == world_id)
        )
        return result.scalar_one()

    async def count_all_commits(self) -> int:
        result = await self.session.execute(
            select(func.count(CommitORM.id))
        )
        return result.scalar_one()

    async def count_worlds(self) -> int:
        result = await self.session.execute(
            select(func.count(WorldORM.id))
        )
        return result.scalar_one()

    async def count_events(self) -> int:
        result = await self.session.execute(
            select(func.count(EventORM.id))
        )
        return result.scalar_one()

    # ── Entity CRUD ───────────────────────────────────────────────────────────

    async def save_entity(self, entity: Entity, world_id: str) -> None:
        entity_orm = EntityORM(
            id=entity.id,
            world_id=world_id,
            name=entity.name,
            entity_type=entity.entity_type.value,
            attributes=entity.attributes,
            created_at_depth=entity.created_at_depth,
            destroyed_at_depth=entity.destroyed_at_depth,
        )
        self.session.add(entity_orm)

    # ── Entity State ───────────────────────────────────────────────────────────

    async def get_entity_state(
        self,
        entity_id: str,
        at_commit: str
    ) -> dict[str, Any] | None:
        """
        For now uses the commit snapshot.
        In a full Phase 2 version, this would use StateRebuilder.
        """
        commit = await self.get_commit(at_commit)
        if commit is None:
            return None

        return commit.entity_states.get(entity_id)

    async def save_entity_snapshot(
        self,
        commit_id: str,
        entity_states: dict[str, Any]
    ) -> None:
        """
        Snapshots are already saved in commit.entity_states_snapshot.
        This method is for future implementations with separate tables.
        """
        pass

    # ── Branches ───────────────────────────────────────────────────────────────

    async def save_branch(self, branch: Branch) -> None:
        branch_orm = BranchORM(
            id=branch.id,
            world_id=branch.world_id,
            origin_commit_id=branch.origin_commit_id,
            leaf_commit_id=branch.leaf_commit_id,
            name=branch.name,
            description=branch.description,
            created_at=branch.created_at,
        )
        self.session.add(branch_orm)
        # Commit handled by get_session() context manager

    async def get_branch(self, branch_id: str) -> Branch | None:
        result = await self.session.execute(
            select(BranchORM).where(BranchORM.id == branch_id)
        )
        branch_orm = result.scalar_one_or_none()

        if branch_orm is None:
            return None

        return Branch(
            id=branch_orm.id,
            world_id=branch_orm.world_id,
            origin_commit_id=branch_orm.origin_commit_id,
            leaf_commit_id=branch_orm.leaf_commit_id,
            name=branch_orm.name,
            description=branch_orm.description,
            created_at=branch_orm.created_at,
        )

    async def list_branches(self, world_id: str) -> list[Branch]:
        result = await self.session.execute(
            select(BranchORM)
            .where(BranchORM.world_id == world_id)
            .order_by(BranchORM.created_at.desc())
        )
        branches_orm = result.scalars().all()

        return [
            Branch(
                id=b.id,
                world_id=b.world_id,
                origin_commit_id=b.origin_commit_id,
                leaf_commit_id=b.leaf_commit_id,
                name=b.name,
                description=b.description,
                created_at=b.created_at,
            )
            for b in branches_orm
        ]

    # ── State Snapshots ────────────────────────────────────────────────────────

    async def get_nearest_snapshot(
        self,
        commit_id: str
    ) -> tuple[str, dict[str, Any]] | None:
        """
        For now returns the snapshot of the commit itself.
        In a full implementation, this would search for periodic snapshots.
        """
        commit = await self.get_commit(commit_id)
        if commit is None:
            return None

        return (commit.id, commit.entity_states)

    async def get_deltas_since(
        self,
        from_commit_id: str,
        to_commit_id: str
    ) -> list[tuple[str, Any]]:
        """
        Returns all deltas applied between two commits.
        Full implementation requires traversing the trunk and accumulating deltas.
        """
        # Placeholder: return empty list for now
        return []

    # ── Conversion helpers ────────────────────────────────────────────────────

    def _world_orm_to_dataclass(self, world_orm: WorldORM) -> WorldDefinition:
        """Converts WorldORM → WorldDefinition."""
        entities = [
            Entity(
                id=e.id,
                name=e.name,
                entity_type=EntityType(e.entity_type),
                attributes=e.attributes,
                created_at_depth=e.created_at_depth,
                destroyed_at_depth=e.destroyed_at_depth,
            )
            for e in world_orm.entities
        ]

        return WorldDefinition(
            id=world_orm.id,
            name=world_orm.name,
            context=world_orm.context,
            protagonist=world_orm.protagonist,
            era=world_orm.era,
            tone=NarrativeTone(world_orm.tone),
            antagonist=world_orm.antagonist,
            rules=world_orm.rules,
            constraints=world_orm.constraints,
            initial_entities=entities,
            dramatic_config=world_orm.dramatic_config,
            max_depth=world_orm.max_depth,
            output_language=world_orm.output_language,
            created_at=world_orm.created_at,
        )

    def _commit_orm_to_dataclass(self, commit_orm: CommitORM) -> NarrativeCommit:
        """Converts CommitORM → NarrativeCommit."""
        dramatic_snapshot = {}
        if commit_orm.dramatic_state:
            dramatic_snapshot = commit_orm.dramatic_state.to_dict()

        return NarrativeCommit(
            id=commit_orm.id,
            world_id=commit_orm.world_id,
            event_id=commit_orm.events[0].id if commit_orm.events else "",
            depth=commit_orm.depth,
            parent_id=commit_orm.parent_id,
            choice_text=commit_orm.choice_text,
            narrative_text=commit_orm.narrative_text,
            summary=commit_orm.summary,
            branch_id=commit_orm.branch_id or str(uuid.uuid4()),
            dramatic_snapshot=dramatic_snapshot,
            world_state_snapshot=commit_orm.world_state_snapshot,
            entity_states=commit_orm.entity_states_snapshot,
            is_ending=commit_orm.is_ending,
            created_at=commit_orm.created_at,
        )

    async def _event_orm_to_dataclass(
        self,
        session: AsyncSession,
        event_orm: EventORM
    ) -> NarrativeEvent:
        """Converts EventORM → NarrativeEvent."""
        # Get cause IDs
        caused_by = [edge.cause_event_id for edge in event_orm.causal_parents]

        # Convert deltas
        entity_deltas = [
            EntityDelta(
                entity_id=d.entity_id,
                entity_name=d.entity_name,
                attribute=d.attribute,
                old_value=d.old_value,
                new_value=d.new_value,
            )
            for d in event_orm.entity_deltas
        ]

        world_deltas = [
            WorldVariableDelta(
                variable=d.variable,
                old_value=d.old_value,
                new_value=d.new_value,
            )
            for d in event_orm.world_deltas
        ]

        # Reconstruct DramaticDelta from dramatic_deltas
        dramatic_delta = DramaticDelta()
        # (For simplicity, we don't reconstruct it here — can be improved)

        return NarrativeEvent(
            id=event_orm.id,
            commit_id=event_orm.commit_id,
            event_type=EventType(event_orm.event_type),
            narrative_text=event_orm.narrative_text,
            summary=event_orm.summary,
            caused_by=caused_by,
            triggered_by_decision=event_orm.triggered_by_decision,
            causal_reason=event_orm.causal_reason,
            entity_deltas=entity_deltas,
            world_deltas=world_deltas,
            dramatic_delta=dramatic_delta,
            forced_by_meter=event_orm.forced_by_meter,
            depth=event_orm.depth,
            created_at=event_orm.created_at,
            topo_order=event_orm.topo_order,
        )
