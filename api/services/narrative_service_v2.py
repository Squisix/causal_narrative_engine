"""
api/services/narrative_service_v2.py - Service with PostgreSQL persistence

Version integrated with Phase 2 (PostgreSQL).
Replaces narrative_service.py which used only in-memory storage.
"""

from typing import Optional

from cne_core.models.world import WorldDefinition, Entity, EntityType
from cne_core.models.commit import NarrativeCommit, NarrativeChoice
from cne_core.models.event import CausalEdge
from cne_core.engine.state_machine import StateMachine, StoryAdvanceResult
from cne_core.interfaces.ai_adapter import NarrativeContext, AIAdapter
from cne_core.interfaces.repository import NarrativeRepository
from persistence.cache import CacheBackend, NullCache

# Module-level engine cache (persists between HTTP requests)
_engine_cache: dict[str, StateMachine] = {}


class NarrativeServiceV2:
    """
    Narrative service with PostgreSQL persistence.

    Persists all worlds/commits in PostgreSQL,
    supports branch navigation and statistics.
    """

    def __init__(self, repository: NarrativeRepository, cache: CacheBackend | None = None):
        """
        Args:
            repository: NarrativeRepository implementation (e.g., PostgreSQLRepository)
            cache: Cache backend (Redis or NullCache). None = no cache.
        """
        self.repo = repository
        self.cache: CacheBackend = cache or NullCache()

        # Per-request choices cache by commit (to avoid double queries)
        self._commit_choices: dict[str, list[NarrativeChoice]] = {}

        # Forced event type cache by commit
        self._commit_forced_event: dict[str, str | None] = {}

    # ── World management ──────────────────────────────────────────────────────

    async def save_world(self, world: WorldDefinition) -> None:
        """Saves a world to PostgreSQL."""
        await self.repo.save_world(world)

    async def get_world(self, world_id: str) -> Optional[WorldDefinition]:
        """Gets a world from cache or PostgreSQL."""
        cached = await self.cache.get_world(world_id)
        if cached:
            return cached
        world = await self.repo.get_world(world_id)
        if world:
            await self.cache.set_world(world_id, world)
        return world

    async def delete_world(self, world_id: str) -> bool:
        """
        Deletes a world and all its commits/events (cascade).

        Returns True if deleted, False if it did not exist.
        """
        deleted = await self.repo.delete_world(world_id)

        if deleted:
            if world_id in _engine_cache:
                del _engine_cache[world_id]
            await self.cache.invalidate_world(world_id)

        return deleted

    # ── Narrative flow ─────────────────────────────────────────────────────────

    async def start_narrative(
        self,
        world_id: str,
        adapter: AIAdapter,
    ) -> NarrativeCommit:
        """
        Starts a new narrative in a world.

        Args:
            world_id: World ID
            adapter: AI adapter to use (mock/anthropic)

        Returns:
            First commit of the narrative
        """
        world = await self.get_world(world_id)
        if not world:
            raise ValueError(f"World not found: {world_id}")

        # Create or retrieve engine
        engine = await self._get_or_create_engine(world_id)

        # Create initial context
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

        # Generate narrative with AI
        proposal = await adapter.generate_narrative(context)

        # Apply to engine
        result = engine.start(
            initial_narrative=proposal.narrative_text,
            initial_choices=proposal.choices,
            initial_summary=proposal.summary,
            initial_dramatic_delta=proposal.dramatic_delta,
            causal_reason=proposal.causal_reason,
        )

        # Extract commit
        commit = result.commit

        # Create and persist branch if this is the first commit
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

        # Persist commit in DB
        await self.repo.save_commit(commit)

        # Persist event and related data
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
        Advances the narrative by making a decision.

        Args:
            commit_id: Current commit ID
            choice: Text of the chosen option
            adapter: AI adapter to use

        Returns:
            New commit
        """
        # Get current commit
        commit = await self.repo.get_commit(commit_id)
        if not commit:
            raise ValueError(f"Commit not found: {commit_id}")

        # Get world
        world = await self.get_world(commit.world_id)
        if not world:
            raise ValueError(f"World not found: {commit.world_id}")

        # Get/create engine
        engine = await self._get_or_create_engine(commit.world_id)

        # Verify the choice is valid (skip for custom player choices)
        player_choice_tone = None
        if not custom_choice:
            commit_choices = await self.get_commit_choices(commit_id)
            valid_choices = [c.text for c in commit_choices]
            if choice not in valid_choices:
                raise ValueError(f"Invalid choice. Valid: {valid_choices}")
            for c in commit_choices:
                if c.text == choice:
                    player_choice_tone = c.tone_hint
                    break

        # If a child with this same choice already exists, navigate to it instead of creating a new one
        existing_children = await self.repo.get_children_commits(commit_id)
        for child in existing_children:
            if child.choice_text == choice:
                engine.go_to_commit(child.id)
                return child

        # Get trunk (cache-aside: Redis -> PostgreSQL)
        trunk = await self.cache.get_trunk(commit_id)
        if not trunk:
            trunk = await self.repo.get_trunk(commit_id, max_depth=20)
            if trunk:
                await self.cache.set_trunk(commit_id, trunk)

        # Evaluate dramatic thresholds
        forced_constraint = engine._dramatic_engine.evaluate_thresholds()

        # Create context
        context = NarrativeContext(
            world_definition=world,
            current_depth=commit.depth + 1,
            current_dramatic_state=commit.dramatic_snapshot or {},
            current_entity_states=commit.entity_states or {},
            current_world_vars=commit.world_state_snapshot or {},
            commit_chain=trunk,
            player_choice=choice,
            player_choice_tone=player_choice_tone,
            forced_constraint=forced_constraint,
        )

        # Generate narrative with AI
        proposal = await adapter.generate_narrative(context)

        # Apply to engine (with entity_deltas, entity_creations, and world_deltas)
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

        # Persist commit in DB
        await self.repo.save_commit(new_commit)

        # Persist event and related data
        await self._persist_result(result)

        return new_commit

    async def goto_commit(self, commit_id: str) -> NarrativeCommit:
        """
        Navigates to a specific commit, restoring the engine state.
        """
        commit = await self.repo.get_commit(commit_id)
        if not commit:
            raise ValueError(f"Commit not found: {commit_id}")

        engine = await self._get_or_create_engine(commit.world_id)
        engine.go_to_commit(commit_id)

        return commit

    # ── Commit queries ─────────────────────────────────────────────────────────

    async def get_commit(self, commit_id: str) -> Optional[NarrativeCommit]:
        """Gets a commit from PostgreSQL."""
        return await self.repo.get_commit(commit_id)

    async def get_commit_choices(self, commit_id: str) -> list[NarrativeChoice]:
        """Gets the choices for a commit (memory -> Redis -> DB)."""
        if commit_id in self._commit_choices:
            return self._commit_choices[commit_id]
        cached = await self.cache.get_choices(commit_id)
        if cached:
            return cached
        choices = await self.repo.get_choices(commit_id)
        if choices:
            await self.cache.set_choices(commit_id, choices)
        return choices

    async def get_dramatic_state(self, commit_id: str) -> Optional[dict[str, int]]:
        """Gets the dramatic state of a commit from DB."""
        commit = await self.get_commit(commit_id)
        if not commit:
            return None

        return commit.dramatic_snapshot

    async def get_forced_event_type(self, commit_id: str) -> Optional[str]:
        """Gets the forced event type (if it exists)."""
        if commit_id in self._commit_forced_event:
            return self._commit_forced_event[commit_id]
        return await self.repo.get_forced_event_type(commit_id)

    # ── Stats ──────────────────────────────────────────────────────────────────

    async def get_world_stats(self, world_id: str) -> dict:
        """Gets statistics for a world from DB."""
        branches = await self.repo.list_branches(world_id)
        total_commits = await self.repo.count_commits(world_id)

        return {
            "total_commits": total_commits,
            "active_branches": len(branches),
        }

    async def get_global_stats(self) -> dict:
        """Gets global statistics."""
        return {
            "total_worlds": await self.repo.count_worlds(),
            "total_commits": await self.repo.count_all_commits(),
            "total_events": await self.repo.count_events(),
        }

    # ── Helpers ────────────────────────────────────────────────────────────────

    async def _persist_result(self, result: StoryAdvanceResult) -> None:
        """Persists event, causal edges, dramatic state/deltas, and choices."""
        commit = result.commit

        # 1. Persist event
        if result.event:
            await self.repo.save_event(result.event)

            # 2. Persist causal edges
            for edge in result.causal_edges:
                await self.repo.save_causal_edge(edge)

            # 3. Persist newly created entities
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

            # 4. Persist individual dramatic deltas (for the paper)
            if result.event.dramatic_delta and not result.event.dramatic_delta.is_empty():
                for meter, value in result.event.dramatic_delta.to_dict().items():
                    if value != 0:
                        await self.repo.save_dramatic_delta(
                            event_id=result.event.id,
                            meter=meter,
                            delta=value,
                        )

        # 5. Persist dramatic state (snapshot)
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

        # 6. Persist choices
        await self.repo.save_choices(commit.id, result.available_choices)
        self._commit_choices[commit.id] = result.available_choices
        self._commit_forced_event[commit.id] = forced_event_str
        await self.cache.set_choices(commit.id, result.available_choices)

    async def _get_or_create_engine(self, world_id: str) -> StateMachine:
        """
        Gets the engine from the global cache, or creates it and rebuilds from DB.
        """
        if world_id in _engine_cache:
            return _engine_cache[world_id]

        world = await self.get_world(world_id)
        if not world:
            raise ValueError(f"World not found: {world_id}")

        engine = StateMachine(world=world)

        # Rebuild from DB: load ALL commits (includes branches)
        all_commits = await self.repo.list_commits(world_id)
        if all_commits:
            engine.rebuild_from_commits(all_commits)

        _engine_cache[world_id] = engine
        return engine
