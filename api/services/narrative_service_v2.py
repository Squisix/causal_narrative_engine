"""
api/services/narrative_service_v2.py - Servicio con persistencia PostgreSQL

Versión integrada con Fase 2 (PostgreSQL).
Reemplaza a narrative_service.py que usaba solo memoria.
"""

from typing import Optional

from cne_core.models.world import WorldDefinition
from cne_core.models.commit import NarrativeCommit, NarrativeChoice
from cne_core.engine.state_machine import StateMachine
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
        Elimina un mundo y todos sus commits/eventos.

        Retorna True si se eliminó, False si no existía.
        """
        world = await self.get_world(world_id)
        if not world:
            return False

        # TODO: Implementar delete en Repository
        # await self.repo.delete_world(world_id)

        # Limpiar engine del cache global
        if world_id in _engine_cache:
            del _engine_cache[world_id]

        return True

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
            current_entity_states={},
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

        # Persistir evento asociado
        # El StateMachine ya creó el evento, lo obtenemos del engine
        # await self.repo.save_event(event)  # TODO: obtener evento del engine

        # Persistir estado dramático
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

        # Persistir choices en BD y cache
        await self.repo.save_choices(commit.id, result.available_choices)
        self._commit_choices[commit.id] = result.available_choices
        self._commit_forced_event[commit.id] = forced_event_str

        return commit

    async def advance_narrative(
        self,
        commit_id: str,
        choice: str,
        adapter: AIAdapter,
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

        # Verificar que la choice es válida
        commit_choices = await self.get_commit_choices(commit_id)
        valid_choices = [c.text for c in commit_choices]
        if choice not in valid_choices:
            raise ValueError(f"Invalid choice. Valid: {valid_choices}")

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

        # Aplicar al engine
        result = engine.advance_story(
            choice_text=choice,
            narrative_text=proposal.narrative_text,
            summary=proposal.summary,
            choices=proposal.choices,
            dramatic_delta=proposal.dramatic_delta,
        )

        # Extraer commit
        new_commit = result.commit

        # Persistir en DB
        await self.repo.save_commit(new_commit)

        # Persistir estado dramático
        forced_event_str = None
        trigger_meter_str = None
        if result.forced_event:
            forced_event_str = result.forced_event.event_type.value
            trigger_meter_str = result.forced_event.trigger_meter

        await self.repo.save_dramatic_state(
            commit_id=new_commit.id,
            vector=result.dramatic_state,
            forced_event=forced_event_str,
            trigger_meter=trigger_meter_str,
        )

        # Persistir choices en BD y cache
        await self.repo.save_choices(new_commit.id, result.available_choices)
        self._commit_choices[new_commit.id] = result.available_choices
        self._commit_forced_event[new_commit.id] = forced_event_str

        return new_commit

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

        # Reconstruir desde BD si hay commits existentes
        latest_id = await self.repo.get_latest_commit_id(world_id)
        if latest_id:
            trunk = await self.repo.get_trunk(latest_id, max_depth=100)
            if trunk:
                engine.rebuild_from_commits(trunk)

        _engine_cache[world_id] = engine
        return engine
