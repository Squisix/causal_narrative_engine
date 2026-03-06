"""
interfaces/repository.py — Contrato de persistencia

Define qué operaciones debe soportar cualquier sistema de persistencia
que se conecte al CNE. El Core Engine solo conoce esta interfaz, no
las implementaciones concretas.

Implementaciones incluidas en el repo:
- InMemoryRepository (Fase 1 ✅, tests sin dependencias)
- PostgreSQLRepository (Fase 2, producción)
- SQLiteRepository (Fase 2, desarrollo local)
"""

from abc import ABC, abstractmethod
from typing import Any

from cne_core.models.world import WorldDefinition, Entity
from cne_core.models.event import NarrativeEvent, CausalEdge
from cne_core.models.commit import NarrativeCommit, Branch


class NarrativeRepository(ABC):
    """
    Interfaz abstracta para persistencia del motor narrativo.

    Todas las operaciones son async porque las implementaciones
    reales (PostgreSQL, SQLite) lo requieren. La implementación
    InMemory también es async por compatibilidad de interfaz.

    Principio: el Core Engine no debe conocer detalles de persistencia.
    Solo llama a estos métodos. La implementación puede usar PostgreSQL,
    MongoDB, archivos JSON, o cualquier otra cosa.
    """

    # ── WorldDefinition ────────────────────────────────────────────────────────

    @abstractmethod
    async def save_world(self, world: WorldDefinition) -> None:
        """Persiste una WorldDefinition (la semilla)."""
        pass

    @abstractmethod
    async def get_world(self, world_id: str) -> WorldDefinition | None:
        """Recupera una WorldDefinition por ID."""
        pass

    @abstractmethod
    async def list_worlds(self, limit: int = 50) -> list[WorldDefinition]:
        """Lista mundos creados (para selección en UI)."""
        pass

    # ── NarrativeCommit ────────────────────────────────────────────────────────

    @abstractmethod
    async def save_commit(self, commit: NarrativeCommit) -> None:
        """
        Persiste un commit narrativo.

        Debe ser una transacción atómica: si falla, no se persiste nada.
        En PostgreSQL esto se maneja con BEGIN/COMMIT.
        """
        pass

    @abstractmethod
    async def get_commit(self, commit_id: str) -> NarrativeCommit | None:
        """Recupera un commit por ID."""
        pass

    @abstractmethod
    async def get_trunk(
        self,
        commit_id: str,
        max_depth: int = 100
    ) -> list[NarrativeCommit]:
        """
        Recupera la cadena de commits desde commit_id hacia atrás.

        Retorna en orden cronológico (del más antiguo al más reciente).
        Si max_depth > 0, limita cuántos commits recuperar.

        Args:
            commit_id: El commit desde donde empezar.
            max_depth: Máximo número de commits a retornar.

        Returns:
            Lista de commits en orden cronológico.
        """
        pass

    @abstractmethod
    async def get_children_commits(self, commit_id: str) -> list[NarrativeCommit]:
        """
        Retorna los commits hijos de un commit dado.

        Útil para navegar ramas alternativas.
        """
        pass

    # ── NarrativeEvent ─────────────────────────────────────────────────────────

    @abstractmethod
    async def save_event(self, event: NarrativeEvent) -> None:
        """Persiste un evento narrativo."""
        pass

    @abstractmethod
    async def get_event(self, event_id: str) -> NarrativeEvent | None:
        """Recupera un evento por ID."""
        pass

    @abstractmethod
    async def get_events_for_commit(self, commit_id: str) -> list[NarrativeEvent]:
        """Retorna todos los eventos asociados a un commit."""
        pass

    # ── Causal Graph ───────────────────────────────────────────────────────────

    @abstractmethod
    async def save_causal_edge(self, edge: CausalEdge) -> None:
        """Persiste una arista del grafo causal."""
        pass

    @abstractmethod
    async def check_causal_path_exists(
        self,
        from_event_id: str,
        to_event_id: str
    ) -> bool:
        """
        Verifica si existe un camino causal de from_event_id a to_event_id.

        Implementación típica: CTE recursiva en SQL.

        Esto es lo que previene ciclos en el DAG:
        Antes de insertar A→B, verificamos que NO exista B→...→A.
        """
        pass

    @abstractmethod
    async def get_causal_parents(self, event_id: str) -> list[str]:
        """Retorna los IDs de los eventos que causaron este evento."""
        pass

    @abstractmethod
    async def get_causal_children(self, event_id: str) -> list[str]:
        """Retorna los IDs de los eventos causados por este evento."""
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
        Persiste el estado del vector dramático en un commit.

        Args:
            commit_id: A qué commit corresponde este estado.
            vector: Los 7 medidores (tension, hope, chaos, etc.).
            forced_event: Tipo de evento forzado si hubo uno.
            trigger_meter: Qué medidor disparó el evento forzado.
        """
        pass

    @abstractmethod
    async def get_dramatic_state(self, commit_id: str) -> dict[str, int] | None:
        """Recupera el vector dramático de un commit."""
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
        Persiste un cambio individual en un medidor dramático.

        Esto se usa para el paper: permite analizar qué eventos
        afectan más cada medidor.

        Args:
            event_id: Evento que causó el cambio.
            meter: Nombre del medidor ("tension", "hope", etc.).
            delta: Cambio en el valor (+15, -8, etc.).
            reason: Explicación opcional del cambio.
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
        Recupera el estado de una entidad en un commit dado.

        En Fase 2, esto usará el StateRebuilder:
        1. Encuentra el snapshot más cercano anterior a at_commit
        2. Aplica todos los deltas desde ahí hasta at_commit

        En Fase 1, se usa directamente el snapshot del commit.
        """
        pass

    @abstractmethod
    async def save_entity_snapshot(
        self,
        commit_id: str,
        entity_states: dict[str, Any]
    ) -> None:
        """
        Guarda un snapshot completo del estado de todas las entidades.

        Se hace periódicamente (ej: cada 10 commits) para optimizar
        la reconstrucción de estado.
        """
        pass

    # ── Branches ───────────────────────────────────────────────────────────────

    @abstractmethod
    async def save_branch(self, branch: Branch) -> None:
        """Persiste metadata de una rama."""
        pass

    @abstractmethod
    async def get_branch(self, branch_id: str) -> Branch | None:
        """Recupera metadata de una rama."""
        pass

    @abstractmethod
    async def list_branches(self, world_id: str) -> list[Branch]:
        """Lista todas las ramas de un mundo."""
        pass

    # ── State Snapshots ────────────────────────────────────────────────────────

    @abstractmethod
    async def get_nearest_snapshot(
        self,
        commit_id: str
    ) -> tuple[str, dict[str, Any]] | None:
        """
        Encuentra el snapshot más cercano anterior a commit_id.

        Retorna: (snapshot_commit_id, entity_states)

        Usado por StateRebuilder para reconstruir estado eficientemente.
        """
        pass

    @abstractmethod
    async def get_deltas_since(
        self,
        from_commit_id: str,
        to_commit_id: str
    ) -> list[tuple[str, Any]]:
        """
        Recupera todos los deltas aplicados entre dos commits.

        Retorna lista de (event_id, deltas) en orden topológico.

        Usado por StateRebuilder.
        """
        pass
