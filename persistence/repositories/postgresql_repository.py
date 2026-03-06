"""
persistence/repositories/postgresql_repository.py

Implementación concreta de NarrativeRepository para PostgreSQL.

Convierte entre:
- Dataclasses del core (WorldDefinition, NarrativeEvent, etc.)
- ORM models de SQLAlchemy (WorldORM, EventORM, etc.)
"""

from sqlalchemy import select, and_
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
from cne_core.models.commit import NarrativeCommit, Branch

from persistence.database import DatabaseConfig
from persistence.models.world_orm import WorldORM, EntityORM
from persistence.models.event_orm import (
    EventORM, CausalEdgeORM, EntityDeltaORM, WorldVariableDeltaORM
)
from persistence.models.commit_orm import CommitORM, BranchORM, DramaticStateORM, DramaticDeltaORM
from persistence.queries.causal_queries import CausalGraphQueries


class PostgreSQLRepository(NarrativeRepository):
    """
    Implementación PostgreSQL de NarrativeRepository.

    Usa SQLAlchemy 2.0 async para todas las operaciones.
    """

    def __init__(self, db_config: DatabaseConfig):
        """
        Args:
            db_config: Configuración de la base de datos.
        """
        self.db_config = db_config

    async def _get_session(self):
        """Helper para obtener una sesión async."""
        async with self.db_config.get_session() as session:
            yield session

    # ── WorldDefinition ────────────────────────────────────────────────────────

    async def save_world(self, world: WorldDefinition) -> None:
        async with self.db_config.get_session() as session:
            # Convertir WorldDefinition a WorldORM
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
                created_at=world.created_at,
            )

            # Convertir entidades iniciales
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
                session.add(entity_orm)

            session.add(world_orm)
            await session.commit()

    async def get_world(self, world_id: str) -> WorldDefinition | None:
        async with self.db_config.get_session() as session:
            result = await session.execute(
                select(WorldORM)
                .options(selectinload(WorldORM.entities))
                .where(WorldORM.id == world_id)
            )
            world_orm = result.scalar_one_or_none()

            if world_orm is None:
                return None

            # Convertir ORM → Dataclass
            return self._world_orm_to_dataclass(world_orm)

    async def list_worlds(self, limit: int = 50) -> list[WorldDefinition]:
        async with self.db_config.get_session() as session:
            result = await session.execute(
                select(WorldORM)
                .options(selectinload(WorldORM.entities))
                .order_by(WorldORM.created_at.desc())
                .limit(limit)
            )
            worlds_orm = result.scalars().all()

            return [self._world_orm_to_dataclass(w) for w in worlds_orm]

    # ── NarrativeCommit ────────────────────────────────────────────────────────

    async def save_commit(self, commit: NarrativeCommit) -> None:
        async with self.db_config.get_session() as session:
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

            session.add(commit_orm)
            await session.commit()

    async def get_commit(self, commit_id: str) -> NarrativeCommit | None:
        async with self.db_config.get_session() as session:
            result = await session.execute(
                select(CommitORM)
                .options(
                    selectinload(CommitORM.dramatic_state),
                    selectinload(CommitORM.events)
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
        Recupera la cadena de commits desde commit_id hacia atrás.
        Retorna en orden cronológico (del más antiguo al más reciente).
        """
        async with self.db_config.get_session() as session:
            commits = []
            current_id = commit_id
            depth = 0

            while current_id and depth < max_depth:
                result = await session.execute(
                    select(CommitORM)
                    .options(
                        selectinload(CommitORM.dramatic_state),
                        selectinload(CommitORM.events)
                    )
                    .where(CommitORM.id == current_id)
                )
                commit_orm = result.scalar_one_or_none()

                if commit_orm is None:
                    break

                commits.append(self._commit_orm_to_dataclass(commit_orm))
                current_id = commit_orm.parent_id
                depth += 1

            # Revertir para tener orden cronológico
            commits.reverse()
            return commits

    async def get_children_commits(self, commit_id: str) -> list[NarrativeCommit]:
        async with self.db_config.get_session() as session:
            result = await session.execute(
                select(CommitORM)
                .options(
                    selectinload(CommitORM.dramatic_state),
                    selectinload(CommitORM.events)
                )
                .where(CommitORM.parent_id == commit_id)
            )
            commits_orm = result.scalars().all()

            return [self._commit_orm_to_dataclass(c) for c in commits_orm]

    # ── NarrativeEvent ─────────────────────────────────────────────────────────

    async def save_event(self, event: NarrativeEvent) -> None:
        async with self.db_config.get_session() as session:
            event_orm = EventORM(
                id=event.id,
                commit_id=event.commit_id,
                event_type=event.event_type.value,
                narrative_text=event.narrative_text,
                summary=event.summary,
                triggered_by_decision=event.triggered_by_decision,
                forced_by_meter=event.forced_by_meter,
                depth=event.depth,
                topo_order=event.topo_order,
                created_at=event.created_at,
            )

            # Agregar event_orm PRIMERO para que los deltas puedan referenciar
            session.add(event_orm)
            await session.flush()  # Force immediate INSERT of event

            # Guardar entity deltas
            for delta in event.entity_deltas:
                delta_orm = EntityDeltaORM(
                    event_id=event.id,
                    entity_id=delta.entity_id,
                    entity_name=delta.entity_name,
                    attribute=delta.attribute,
                    old_value=delta.old_value,
                    new_value=delta.new_value,
                )
                session.add(delta_orm)

            # Guardar world deltas
            for delta in event.world_deltas:
                delta_orm = WorldVariableDeltaORM(
                    event_id=event.id,
                    variable=delta.variable,
                    old_value=delta.old_value,
                    new_value=delta.new_value,
                )
                session.add(delta_orm)

            # Guardar dramatic deltas
            if not event.dramatic_delta.is_empty():
                for meter, value in event.dramatic_delta.to_dict().items():
                    if value != 0:
                        delta_orm = DramaticDeltaORM(
                            event_id=event.id,
                            meter=meter,
                            delta=value,
                        )
                        session.add(delta_orm)

            await session.commit()

    async def get_event(self, event_id: str) -> NarrativeEvent | None:
        async with self.db_config.get_session() as session:
            result = await session.execute(
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

            return await self._event_orm_to_dataclass(session, event_orm)

    async def get_events_for_commit(self, commit_id: str) -> list[NarrativeEvent]:
        async with self.db_config.get_session() as session:
            result = await session.execute(
                select(EventORM)
                .options(
                    selectinload(EventORM.entity_deltas),
                    selectinload(EventORM.world_deltas),
                    selectinload(EventORM.causal_parents),
                )
                .where(EventORM.commit_id == commit_id)
            )
            events_orm = result.scalars().all()

            return [await self._event_orm_to_dataclass(session, e) for e in events_orm]

    # ── Causal Graph ───────────────────────────────────────────────────────────

    async def save_causal_edge(self, edge: CausalEdge) -> None:
        async with self.db_config.get_session() as session:
            # PRIMERO: verificar que no exista ciclo
            path_exists = await CausalGraphQueries.check_causal_path_exists(
                session,
                edge.effect_event_id,  # Desde el efecto
                edge.cause_event_id    # Hacia la causa
            )

            if path_exists:
                raise ValueError(
                    f"No se puede crear la arista {edge.cause_event_id[:8]}... -> "
                    f"{edge.effect_event_id[:8]}... porque crearia un ciclo."
                )

            # OK, no hay ciclo. Guardar la arista.
            edge_orm = CausalEdgeORM(
                id=edge.id,
                cause_event_id=edge.cause_event_id,
                effect_event_id=edge.effect_event_id,
                relation_type=edge.relation_type.value,
                strength=edge.strength,
            )

            session.add(edge_orm)
            await session.commit()

    async def check_causal_path_exists(
        self,
        from_event_id: str,
        to_event_id: str
    ) -> bool:
        async with self.db_config.get_session() as session:
            return await CausalGraphQueries.check_causal_path_exists(
                session,
                from_event_id,
                to_event_id
            )

    async def get_causal_parents(self, event_id: str) -> list[str]:
        async with self.db_config.get_session() as session:
            result = await session.execute(
                select(CausalEdgeORM.cause_event_id)
                .where(CausalEdgeORM.effect_event_id == event_id)
            )
            return [row[0] for row in result.fetchall()]

    async def get_causal_children(self, event_id: str) -> list[str]:
        async with self.db_config.get_session() as session:
            result = await session.execute(
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
        async with self.db_config.get_session() as session:
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

            session.add(dramatic_state)
            await session.commit()

    async def get_dramatic_state(self, commit_id: str) -> dict[str, int] | None:
        async with self.db_config.get_session() as session:
            result = await session.execute(
                select(DramaticStateORM)
                .where(DramaticStateORM.commit_id == commit_id)
            )
            state = result.scalar_one_or_none()

            if state is None:
                return None

            return state.to_dict()

    async def save_dramatic_delta(
        self,
        event_id: str,
        meter: str,
        delta: int,
        reason: str | None = None
    ) -> None:
        async with self.db_config.get_session() as session:
            delta_orm = DramaticDeltaORM(
                event_id=event_id,
                meter=meter,
                delta=delta,
                reason=reason,
            )
            session.add(delta_orm)
            await session.commit()

    # ── Entity State ───────────────────────────────────────────────────────────

    async def get_entity_state(
        self,
        entity_id: str,
        at_commit: str
    ) -> dict[str, Any] | None:
        """
        Por ahora usa el snapshot del commit.
        En una versión completa de Fase 2, usaría StateRebuilder.
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
        Los snapshots ya se guardan en commit.entity_states_snapshot.
        Este método es para implementaciones futuras con tablas separadas.
        """
        pass

    # ── Branches ───────────────────────────────────────────────────────────────

    async def save_branch(self, branch: Branch) -> None:
        async with self.db_config.get_session() as session:
            branch_orm = BranchORM(
                id=branch.id,
                world_id=branch.world_id,
                origin_commit_id=branch.origin_commit_id,
                leaf_commit_id=branch.leaf_commit_id,
                name=branch.name,
                description=branch.description,
                created_at=branch.created_at,
            )
            session.add(branch_orm)
            await session.commit()

    async def get_branch(self, branch_id: str) -> Branch | None:
        async with self.db_config.get_session() as session:
            result = await session.execute(
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
        async with self.db_config.get_session() as session:
            result = await session.execute(
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
        Por ahora retorna el snapshot del commit mismo.
        En una implementación completa, buscaría snapshots periódicos.
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
        Retorna todos los deltas aplicados entre dos commits.
        Implementación completa requiere recorrer el trunk y acumular deltas.
        """
        # Placeholder: retornar lista vacía por ahora
        return []

    # ── Helpers de conversión ──────────────────────────────────────────────────

    def _world_orm_to_dataclass(self, world_orm: WorldORM) -> WorldDefinition:
        """Convierte WorldORM → WorldDefinition."""
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
            created_at=world_orm.created_at,
        )

    def _commit_orm_to_dataclass(self, commit_orm: CommitORM) -> NarrativeCommit:
        """Convierte CommitORM → NarrativeCommit."""
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
        """Convierte EventORM → NarrativeEvent."""
        # Obtener IDs de causas
        caused_by = [edge.cause_event_id for edge in event_orm.causal_parents]

        # Convertir deltas
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

        # Reconstruir DramaticDelta desde dramatic_deltas
        dramatic_delta = DramaticDelta()
        # (Por simplicidad, no lo reconstruimos aquí — se puede mejorar)

        return NarrativeEvent(
            id=event_orm.id,
            commit_id=event_orm.commit_id,
            event_type=EventType(event_orm.event_type),
            narrative_text=event_orm.narrative_text,
            summary=event_orm.summary,
            caused_by=caused_by,
            triggered_by_decision=event_orm.triggered_by_decision,
            entity_deltas=entity_deltas,
            world_deltas=world_deltas,
            dramatic_delta=dramatic_delta,
            forced_by_meter=event_orm.forced_by_meter,
            depth=event_orm.depth,
            created_at=event_orm.created_at,
            topo_order=event_orm.topo_order,
        )
