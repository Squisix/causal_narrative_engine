"""
persistence/state_rebuilder.py — Reconstrucción de estado desde deltas

En Fase 1, el estado completo se guarda en cada commit (snapshots).
En Fase 2, optimizamos guardando solo deltas y reconstruyendo el estado
cuando sea necesario.

Algoritmo:
1. Encontrar el snapshot más cercano anterior al commit objetivo
2. Recuperar todos los deltas desde ese snapshot hasta el commit objetivo
3. Aplicar los deltas en orden topológico
4. Retornar el estado reconstruido

Esto permite:
- Reducir espacio en DB (no guardar estado completo en cada commit)
- Reconstruir estado en cualquier punto de la historia
- Validar coherencia del estado a lo largo del tiempo
"""

from typing import Any, Dict, List, Tuple
from dataclasses import dataclass

from cne_core.interfaces.repository import NarrativeRepository
from cne_core.models.event import NarrativeEvent, EntityDelta, WorldVariableDelta


@dataclass
class WorldState:
    """
    Estado completo del mundo en un momento dado.

    Esto es lo que StateRebuilder retorna después de reconstruir.
    """
    commit_id: str
    depth: int

    # Estado de entidades: {entity_id: {atributos}}
    entity_states: Dict[str, Dict[str, Any]]

    # Variables globales del mundo
    world_variables: Dict[str, Any]

    # Vector dramático
    dramatic_vector: Dict[str, int]

    def get_entity_attribute(
        self,
        entity_id: str,
        attribute: str,
        default: Any = None
    ) -> Any:
        """Acceso seguro a atributos de entidades."""
        entity = self.entity_states.get(entity_id)
        if entity is None:
            return default
        return entity.get(attribute, default)

    def get_world_variable(self, variable: str, default: Any = None) -> Any:
        """Acceso seguro a variables del mundo."""
        return self.world_variables.get(variable, default)

    def get_dramatic_meter(self, meter: str, default: int = 0) -> int:
        """Acceso seguro a medidores dramáticos."""
        return self.dramatic_vector.get(meter, default)


class StateRebuilder:
    """
    Reconstruye el estado del mundo en cualquier commit.

    Estrategia:
    - Si hay snapshot en el commit: usar ese
    - Si no: buscar snapshot más cercano + aplicar deltas

    Optimización:
    - Guardar snapshots periódicos (cada 10 commits, configurable)
    - Cachear estados reconstruidos en memoria (LRU cache)
    """

    def __init__(
        self,
        repository: NarrativeRepository,
        snapshot_frequency: int = 10
    ):
        """
        Args:
            repository: Repository para acceder a commits y eventos.
            snapshot_frequency: Cada cuántos commits guardar un snapshot completo.
        """
        self.repository = repository
        self.snapshot_frequency = snapshot_frequency

    async def rebuild_from_commit(
        self,
        commit_id: str
    ) -> WorldState | None:
        """
        Reconstruye el estado completo del mundo en un commit dado.

        Args:
            commit_id: Commit objetivo.

        Returns:
            WorldState reconstruido, o None si el commit no existe.
        """
        # 1. Obtener el commit
        commit = await self.repository.get_commit(commit_id)
        if commit is None:
            return None

        # 2. Si el commit tiene snapshot completo, usarlo directamente
        if commit.entity_states and commit.world_state_snapshot:
            return WorldState(
                commit_id=commit.id,
                depth=commit.depth,
                entity_states=commit.entity_states.copy(),
                world_variables=commit.world_state_snapshot.copy(),
                dramatic_vector=commit.dramatic_snapshot.copy(),
            )

        # 3. Si no, buscar snapshot más cercano
        snapshot_result = await self.repository.get_nearest_snapshot(commit_id)
        if snapshot_result is None:
            # No hay snapshots previos, el commit raíz debería tener snapshot
            return WorldState(
                commit_id=commit.id,
                depth=commit.depth,
                entity_states={},
                world_variables={},
                dramatic_vector=commit.dramatic_snapshot.copy(),
            )

        snapshot_commit_id, entity_states = snapshot_result

        # 4. Obtener deltas desde el snapshot hasta el commit objetivo
        deltas = await self.repository.get_deltas_since(
            snapshot_commit_id,
            commit_id
        )

        # 5. Aplicar deltas en orden
        current_state = WorldState(
            commit_id=commit_id,
            depth=commit.depth,
            entity_states=entity_states.copy(),
            world_variables={},
            dramatic_vector=commit.dramatic_snapshot.copy(),
        )

        for event_id, event_deltas in deltas:
            self._apply_event_deltas(current_state, event_deltas)

        return current_state

    async def should_create_snapshot(self, commit_depth: int) -> bool:
        """
        Determina si se debe crear un snapshot en este commit.

        Args:
            commit_depth: Profundidad del commit actual.

        Returns:
            True si se debe crear snapshot.
        """
        return commit_depth % self.snapshot_frequency == 0

    async def create_snapshot(self, commit_id: str, state: WorldState) -> None:
        """
        Guarda un snapshot completo del estado.

        Args:
            commit_id: Commit en el que guardar el snapshot.
            state: Estado a guardar.
        """
        await self.repository.save_entity_snapshot(
            commit_id,
            state.entity_states
        )

    def _apply_event_deltas(
        self,
        state: WorldState,
        event_deltas: Any
    ) -> None:
        """
        Aplica los deltas de un evento al estado actual.

        Modifica state in-place.

        Args:
            state: Estado a modificar.
            event_deltas: Deltas del evento (EntityDelta, WorldVariableDelta).
        """
        # Este método necesita acceder a los deltas del evento
        # En una implementación completa, event_deltas sería un objeto
        # con listas de EntityDelta y WorldVariableDelta

        # Por ahora es un placeholder
        pass

    async def validate_state_consistency(
        self,
        commit_id: str
    ) -> Dict[str, Any]:
        """
        Valida que el estado reconstruido sea consistente.

        Útil para debugging y para el paper.

        Args:
            commit_id: Commit a validar.

        Returns:
            Dict con resultados de validación:
            {
                "is_valid": bool,
                "errors": list[str],
                "warnings": list[str],
            }
        """
        state = await self.rebuild_from_commit(commit_id)
        if state is None:
            return {
                "is_valid": False,
                "errors": [f"Commit {commit_id[:8]}... no existe"],
                "warnings": [],
            }

        errors = []
        warnings = []

        # Validar que entidades muertas no tengan is_alive=True
        for entity_id, entity_state in state.entity_states.items():
            if not entity_state.get("alive", True):
                # Entidad marcada como muerta
                # Podríamos validar que no tenga acciones posteriores
                pass

        # Validar que medidores dramáticos estén en rango
        for meter, value in state.dramatic_vector.items():
            if not (0 <= value <= 100):
                errors.append(
                    f"Medidor {meter} fuera de rango: {value} (debe estar en [0,100])"
                )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


class DeltaAccumulator:
    """
    Helper para acumular deltas durante la reconstrucción.

    Mantiene track de qué atributos han cambiado y en qué orden.
    """

    def __init__(self):
        self.entity_deltas: List[EntityDelta] = []
        self.world_deltas: List[WorldVariableDelta] = []

    def add_entity_delta(self, delta: EntityDelta) -> None:
        """Registra un cambio en una entidad."""
        self.entity_deltas.append(delta)

    def add_world_delta(self, delta: WorldVariableDelta) -> None:
        """Registra un cambio en una variable del mundo."""
        self.world_deltas.append(delta)

    def apply_to_state(self, state: WorldState) -> None:
        """
        Aplica todos los deltas acumulados a un WorldState.

        Modifica state in-place.
        """
        # Aplicar entity deltas
        for delta in self.entity_deltas:
            if delta.entity_id not in state.entity_states:
                state.entity_states[delta.entity_id] = {}

            state.entity_states[delta.entity_id][delta.attribute] = delta.new_value

        # Aplicar world deltas
        for delta in self.world_deltas:
            state.world_variables[delta.variable] = delta.new_value

    def get_summary(self) -> str:
        """Resumen de los deltas acumulados (para logging)."""
        return (
            f"{len(self.entity_deltas)} entity deltas, "
            f"{len(self.world_deltas)} world deltas"
        )
