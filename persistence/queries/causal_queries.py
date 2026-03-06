"""
persistence/queries/causal_queries.py — Queries para el grafo causal

La query más importante: validar que no existan ciclos en el DAG.

Antes de insertar A→B, verificamos que NO exista un camino B→...→A.
Esto se hace con una CTE recursiva.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List


class CausalGraphQueries:
    """
    Queries especializadas para el grafo causal.

    Todas las queries son async y retornan resultados procesados.
    """

    @staticmethod
    async def check_causal_path_exists(
        session: AsyncSession,
        from_event_id: str,
        to_event_id: str
    ) -> bool:
        """
        Verifica si existe un camino causal de from_event_id a to_event_id.

        Usa una CTE recursiva para recorrer el grafo.

        Esta es la query que previene ciclos:
        Antes de insertar A→B, llamamos a check_causal_path_exists(B, A).
        Si retorna True, significa que ya existe B→...→A, y crear A→B
        crearía un ciclo.

        Args:
            session: Sesión async de SQLAlchemy.
            from_event_id: Evento inicial del camino.
            to_event_id: Evento final que buscamos alcanzar.

        Returns:
            True si existe un camino, False si no.
        """
        query = text("""
            WITH RECURSIVE causal_path AS (
                -- Caso base: empezamos desde from_event_id
                SELECT
                    cause_event_id,
                    effect_event_id,
                    1 AS depth
                FROM event_edges
                WHERE cause_event_id = :from_event_id

                UNION

                -- Caso recursivo: seguimos las aristas causales
                SELECT
                    e.cause_event_id,
                    e.effect_event_id,
                    p.depth + 1
                FROM event_edges e
                INNER JOIN causal_path p ON e.cause_event_id = p.effect_event_id
                WHERE p.depth < 100  -- Límite de seguridad contra loops infinitos
            )
            SELECT 1
            FROM causal_path
            WHERE effect_event_id = :to_event_id
            LIMIT 1
        """)

        result = await session.execute(
            query,
            {"from_event_id": from_event_id, "to_event_id": to_event_id}
        )
        return result.scalar() is not None

    @staticmethod
    async def get_causal_ancestors(
        session: AsyncSession,
        event_id: str,
        max_depth: int = 50
    ) -> List[str]:
        """
        Retorna todos los ancestros causales de un evento.

        Ancestros = eventos que causaron este, directa o indirectamente.

        Args:
            session: Sesión async.
            event_id: Evento del cual buscar ancestros.
            max_depth: Máxima profundidad de búsqueda.

        Returns:
            Lista de event_ids ancestros, ordenados por topo_order.
        """
        query = text("""
            WITH RECURSIVE ancestors AS (
                -- Caso base: padres directos
                SELECT
                    e.cause_event_id AS ancestor_id,
                    1 AS depth
                FROM event_edges e
                WHERE e.effect_event_id = :event_id

                UNION

                -- Caso recursivo: subir por el árbol
                SELECT
                    e.cause_event_id,
                    a.depth + 1
                FROM event_edges e
                INNER JOIN ancestors a ON e.effect_event_id = a.ancestor_id
                WHERE a.depth < :max_depth
            )
            SELECT DISTINCT ancestor_id
            FROM ancestors
            ORDER BY ancestor_id
        """)

        result = await session.execute(
            query,
            {"event_id": event_id, "max_depth": max_depth}
        )
        return [row[0] for row in result.fetchall()]

    @staticmethod
    async def get_causal_descendants(
        session: AsyncSession,
        event_id: str,
        max_depth: int = 50
    ) -> List[str]:
        """
        Retorna todos los descendientes causales de un evento.

        Descendientes = eventos causados por este, directa o indirectamente.

        Args:
            session: Sesión async.
            event_id: Evento del cual buscar descendientes.
            max_depth: Máxima profundidad de búsqueda.

        Returns:
            Lista de event_ids descendientes.
        """
        query = text("""
            WITH RECURSIVE descendants AS (
                -- Caso base: hijos directos
                SELECT
                    e.effect_event_id AS descendant_id,
                    1 AS depth
                FROM event_edges e
                WHERE e.cause_event_id = :event_id

                UNION

                -- Caso recursivo: bajar por el árbol
                SELECT
                    e.effect_event_id,
                    d.depth + 1
                FROM event_edges e
                INNER JOIN descendants d ON e.cause_event_id = d.descendant_id
                WHERE d.depth < :max_depth
            )
            SELECT DISTINCT descendant_id
            FROM descendants
            ORDER BY descendant_id
        """)

        result = await session.execute(
            query,
            {"event_id": event_id, "max_depth": max_depth}
        )
        return [row[0] for row in result.fetchall()]

    @staticmethod
    async def get_topological_order(
        session: AsyncSession,
        world_id: str
    ) -> List[str]:
        """
        Retorna todos los eventos de un mundo en orden topológico.

        Orden topológico: si A causó B, entonces A aparece antes que B.

        Esto es útil para:
        - Reconstruir el estado desde el inicio
        - Exportar la historia completa
        - Validar que el DAG es coherente

        Args:
            session: Sesión async.
            world_id: Mundo del cual obtener eventos.

        Returns:
            Lista de event_ids en orden topológico.
        """
        query = text("""
            WITH RECURSIVE topo_sort AS (
                -- Caso base: eventos raíz (sin padres)
                SELECT
                    e.id AS event_id,
                    0 AS level
                FROM events e
                INNER JOIN commits c ON e.commit_id = c.id
                WHERE c.world_id = :world_id
                  AND NOT EXISTS (
                      SELECT 1
                      FROM event_edges edge
                      WHERE edge.effect_event_id = e.id
                  )

                UNION

                -- Caso recursivo: eventos con todos sus padres ya procesados
                SELECT
                    e.id,
                    ts.level + 1
                FROM events e
                INNER JOIN commits c ON e.commit_id = c.id
                INNER JOIN event_edges edge ON edge.effect_event_id = e.id
                INNER JOIN topo_sort ts ON edge.cause_event_id = ts.event_id
                WHERE c.world_id = :world_id
            )
            SELECT DISTINCT event_id
            FROM topo_sort
            ORDER BY level, event_id
        """)

        result = await session.execute(query, {"world_id": world_id})
        return [row[0] for row in result.fetchall()]

    @staticmethod
    async def get_causal_graph_stats(
        session: AsyncSession,
        world_id: str
    ) -> dict:
        """
        Estadísticas del grafo causal para un mundo.

        Útil para el paper y para debugging.

        Returns:
            Dict con: total_events, total_edges, avg_causes_per_event,
                      root_events, leaf_events
        """
        query = text("""
            WITH event_stats AS (
                SELECT
                    e.id,
                    COUNT(DISTINCT in_edge.id) AS num_causes,
                    COUNT(DISTINCT out_edge.id) AS num_effects
                FROM events e
                INNER JOIN commits c ON e.commit_id = c.id
                LEFT JOIN event_edges in_edge ON in_edge.effect_event_id = e.id
                LEFT JOIN event_edges out_edge ON out_edge.cause_event_id = e.id
                WHERE c.world_id = :world_id
                GROUP BY e.id
            )
            SELECT
                COUNT(*) AS total_events,
                SUM(num_causes) AS total_edges,
                AVG(num_causes) AS avg_causes_per_event,
                SUM(CASE WHEN num_causes = 0 THEN 1 ELSE 0 END) AS root_events,
                SUM(CASE WHEN num_effects = 0 THEN 1 ELSE 0 END) AS leaf_events
            FROM event_stats
        """)

        result = await session.execute(query, {"world_id": world_id})
        row = result.fetchone()

        if row is None:
            return {
                "total_events": 0,
                "total_edges": 0,
                "avg_causes_per_event": 0.0,
                "root_events": 0,
                "leaf_events": 0,
            }

        return {
            "total_events": int(row[0] or 0),
            "total_edges": int(row[1] or 0),
            "avg_causes_per_event": float(row[2] or 0.0),
            "root_events": int(row[3] or 0),
            "leaf_events": int(row[4] or 0),
        }
