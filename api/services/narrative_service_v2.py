"""
api/services/narrative_service_v2.py - Servicio con persistencia PostgreSQL

Versión integrada con Fase 2 (PostgreSQL).
Reemplaza a narrative_service.py que usaba solo memoria.
"""

from typing import Optional

from cne_core.models.world import WorldDefinition, Entity, EntityType
from cne_core.models.commit import NarrativeCommit, NarrativeChoice
from cne_core.models.event import CausalEdge
from cne_core.engine.state_machine import StateMachine, StoryAdvanceResult
from cne_core.interfaces.ai_adapter import NarrativeContext, AIAdapter
from cne_core.interfaces.repository import NarrativeRepository

# Cache de engines a nivel de módulo (persiste entre requests HTTP)
_engine_cache: dict[str, StateMachine] = {}


class NarrativeServiceV2:
    """
    Servicio de narrativa con persistencia PostgreSQL.

    Persiste todos los mundos/commits en PostgreSQL,
    soporta navegación de branches y estadísticas.
    """

    def __init__(self, repository: NarrativeRepository):
        """
        Args:
            repository: Implementación de NarrativeRepository (ej: PostgreSQLRepository)
        """
        self.repo = repository

        # Cache de choices por commit (per-request, para evitar doble query)
        self._commit_choices: dict[str, list[NarrativeChoice]] = {}

        # Cache de forced event type por commit
        self._commit_forced_event: dict[str, str | None] = {}

    # ── World management ──────────────────────────────────────────────────────

    async def save_world(self, world: WorldDefinition) -> None:
        """Guarda un mundo en PostgreSQL."""
        await self.repo.save_world(world)

    async def get_world(self, world_id: str) -> Optional[WorldDefinition]:
        """Obtiene un mundo desde PostgreSQL."""
        return await self.repo.get_world(world_id)

    async def delete_world(self, world_id: str) -> bool:
        """
        Elimina un mundo y todos sus commits/eventos (cascade).

        Retorna True si se eliminó, False si no existía.
        """
        deleted = await self.repo.delete_world(world_id)

        if deleted and world_id in _engine_cache:
            del _engine_cache[world_id]

        return deleted

    # ── Narrative flow ─────────────────────────────────────────────────────────

    async def start_narrative(
        self,
        world_id: str,
        adapter: AIAdapter,
    ) -> NarrativeCommit:
        """
        Inicia una nueva narrativa en un mundo.

        Args:
            world_id: ID del mundo
            adapter: AI adapter a usar (mock/anthropic)

        Returns:
            Primer commit de la narrativa
        """
        world = await self.get_world(world_id)
        if not world:
            raise ValueError(f"World not found: {world_id}")

        # Crear o recuperar engine
        engine = await self._get_or_create_engine(world_id)

        # Crear contexto inicial
        context = NarrativeContext(
            world_definition=world,
            current_depth=0,
            current_dramatic_state={
                "tension": world.dramatic_config.get("tension", 30),
                "hope": world.dramatic_config.get("hope", 60),
                "chaos": world.dramatic_config.get("chaos", 20),
                "rhythm": world.dramatic_config.get("rhythm", 50),
                "saturation": world.dramatic_config.get("saturation", 0),
                "connection": world.dramatic_config.get("connection", 40),
                "mystery": world.dramatic_config.get("mystery", 50),
            },
            current_entity_states=engine._get_entity_states(),
            current_world_vars={},
            commit_chain=[],
            player_choice=None,
            forced_constraint=None,
        )

        # Generar narrativa con IA
        proposal = await adapter.generate_narrative(context)

        # Aplicar al engine
        result = engine.start(
            initial_narrative=proposal.narrative_text,
            initial_choices=proposal.choices,
            initial_summary=proposal.summary,
            initial_dramatic_delta=proposal.dramatic_delta,
            causal_reason=proposal.causal_reason,
        )

        # Extraer commit
        commit = result.commit

        # Crear y persistir branch si es el primer commit
        if commit.depth == 0:
            from cne_core.models.commit import Branch
            branch = Branch(
                id=commit.branch_id,
                world_id=world_id,
                origin_commit_id=commit.id,
                leaf_commit_id=commit.id,
                name="main",
                description="Main narrative branch"
            )
            await self.repo.save_branch(branch)

        # Persistir commit en DB
        await self.repo.save_commit(commit)

        # Persistir evento y datos relacionados
        await self._persist_result(result)

        return commit

    async def advance_narrative(
        self,
        commit_id: str,
        choice: str,
        adapter: AIAdapter,
        custom_choice: bool = False,
    ) -> NarrativeCommit:
        """
        Avanza la narrativa tomando una decisión.

        Args:
            commit_id: ID del commit actual
            choice: Texto de la opción elegida
            adapter: AI adapter a usar

        Returns:
            Nuevo commit
        """
        # Obtener commit actual
        commit = await self.repo.get_commit(commit_id)
        if not commit:
            raise ValueError(f"Commit not found: {commit_id}")

        # Obtener world
        world = await self.get_world(commit.world_id)
        if not world:
            raise ValueError(f"World not found: {commit.world_id}")

        # Obtener/crear engine
        engine = await self._get_or_create_engine(commit.world_id)

        # Verificar que la choice es válida (skip para opciones custom del jugador)
        if not custom_choice:
            commit_choices = await self.get_commit_choices(commit_id)
            valid_choices = [c.text for c in commit_choices]
            if choice not in valid_choices:
                raise ValueError(f"Invalid choice. Valid: {valid_choices}")

        # Si ya existe un hijo con esta misma choice, navegar a él en vez de crear uno nuevo
        existing_children = await self.repo.get_children_commits(commit_id)
        for child in existing_children:
            if child.choice_text == choice:
                engine.go_to_commit(child.id)
                return child

        # Obtener trunk completo desde DB
        trunk = await self.repo.get_trunk(commit_id, max_depth=20)

        # Evaluar umbrales dramáticos
        forced_constraint = engine._dramatic_engine.evaluate_thresholds()

        # Crear contexto
        context = NarrativeContext(
            world_definition=world,
            current_depth=commit.depth + 1,
            current_dramatic_state=commit.dramatic_snapshot or {},
            current_entity_states=commit.entity_states or {},
            current_world_vars=commit.world_state_snapshot or {},
            commit_chain=trunk,
            player_choice=choice,
            forced_constraint=forced_constraint,
        )

        # Generar narrativa con IA
        proposal = await adapter.generate_narrative(context)

        # Aplicar al engine (con entity_deltas, entity_creations y world_deltas)
        result = engine.advance_story(
            choice_text=choice,
            narrative_text=proposal.narrative_text,
            summary=proposal.summary,
            choices=proposal.choices,
            entity_deltas=proposal.entity_deltas if proposal.entity_deltas else None,
            entity_creations=proposal.entity_creations if proposal.entity_creations else None,
            world_deltas=proposal.world_deltas if proposal.world_deltas else None,
            dramatic_delta=proposal.dramatic_delta,
            is_ending=proposal.is_ending,
            causal_reason=proposal.causal_reason,
        )

        new_commit = result.commit

        # Persistir commit en DB
        await self.repo.save_commit(new_commit)

        # Persistir evento y datos relacionados
        await self._persist_result(result)

        return new_commit

    async def goto_commit(self, commit_id: str) -> NarrativeCommit:
        """
        Navega a un commit específico, restaurando el estado del engine.
        """
        commit = await self.repo.get_commit(commit_id)
        if not commit:
            raise ValueError(f"Commit not found: {commit_id}")

        engine = await self._get_or_create_engine(commit.world_id)
        engine.go_to_commit(commit_id)

        return commit

    # ── Commit queries ─────────────────────────────────────────────────────────

    async def get_commit(self, commit_id: str) -> Optional[NarrativeCommit]:
        """Obtiene un commit desde PostgreSQL."""
        return await self.repo.get_commit(commit_id)

    async def get_commit_choices(self, commit_id: str) -> list[NarrativeChoice]:
        """Obtiene las choices de un commit (cache o BD)."""
        if commit_id in self._commit_choices:
            return self._commit_choices[commit_id]
        return await self.repo.get_choices(commit_id)

    async def get_dramatic_state(self, commit_id: str) -> Optional[dict[str, int]]:
        """Obtiene el estado dramático de un commit desde DB."""
        commit = await self.get_commit(commit_id)
        if not commit:
            return None

        return commit.dramatic_snapshot

    async def get_forced_event_type(self, commit_id: str) -> Optional[str]:
        """Obtiene el tipo de evento forzado (si existe)."""
        if commit_id in self._commit_forced_event:
            return self._commit_forced_event[commit_id]
        return await self.repo.get_forced_event_type(commit_id)

    # ── Stats ──────────────────────────────────────────────────────────────────

    async def get_world_stats(self, world_id: str) -> dict:
        """Obtiene estadísticas de un mundo desde DB."""
        branches = await self.repo.list_branches(world_id)
        total_commits = await self.repo.count_commits(world_id)

        return {
            "total_commits": total_commits,
            "active_branches": len(branches),
        }

    async def get_global_stats(self) -> dict:
        """Obtiene estadísticas globales."""
        return {
            "total_worlds": await self.repo.count_worlds(),
            "total_commits": await self.repo.count_all_commits(),
            "total_events": await self.repo.count_events(),
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _persist_result(self, result: StoryAdvanceResult) -> None:
        """Persiste evento, aristas causales, dramatic state/deltas, y choices."""
        commit = result.commit

        # 1. Persistir evento
        if result.event:
            await self.repo.save_event(result.event)

            # 2. Persistir aristas causales
            for edge in result.causal_edges:
                await self.repo.save_causal_edge(edge)

            # 3. Persistir nuevas entidades creadas
            for creation in result.event.entity_creations:
                entity_type_map = {
                    "character": EntityType.CHARACTER,
                    "faction": EntityType.FACTION,
                    "artifact": EntityType.ARTIFACT,
                    "location": EntityType.LOCATION,
                }
                etype = entity_type_map.get(creation.entity_type.lower(), EntityType.CHARACTER)
                entity = Entity(
                    id=creation.entity_id,
                    name=creation.entity_name,
                    entity_type=etype,
                    attributes=creation.attributes,
                    created_at_depth=result.event.depth,
                )
                await self.repo.save_entity(entity, commit.world_id)

            # 4. Persistir dramatic deltas individuales (para el paper)
            if result.event.dramatic_delta and not result.event.dramatic_delta.is_empty():
                for meter, value in result.event.dramatic_delta.to_dict().items():
                    if value != 0:
                        await self.repo.save_dramatic_delta(
                            event_id=result.event.id,
                            meter=meter,
                            delta=value,
                        )

        # 5. Persistir estado dramático (snapshot)
        forced_event_str = None
        trigger_meter_str = None
        if result.forced_event:
            forced_event_str = result.forced_event.event_type.value
            trigger_meter_str = result.forced_event.trigger_meter

        await self.repo.save_dramatic_state(
            commit_id=commit.id,
            vector=result.dramatic_state,
            forced_event=forced_event_str,
            trigger_meter=trigger_meter_str,
        )

        # 6. Persistir choices
        await self.repo.save_choices(commit.id, result.available_choices)
        self._commit_choices[commit.id] = result.available_choices
        self._commit_forced_event[commit.id] = forced_event_str

    async def _get_or_create_engine(self, world_id: str) -> StateMachine:
        """
        Obtiene el engine del cache global, o lo crea y reconstruye desde BD.
        """
        if world_id in _engine_cache:
            return _engine_cache[world_id]

        world = await self.get_world(world_id)
        if not world:
            raise ValueError(f"World not found: {world_id}")

        engine = StateMachine(world=world)

        # Reconstruir desde BD: cargar TODOS los commits (incluye ramas)
        all_commits = await self.repo.list_commits(world_id)
        if all_commits:
            engine.rebuild_from_commits(all_commits)

        _engine_cache[world_id] = engine
        return engine
