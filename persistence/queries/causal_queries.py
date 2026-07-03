"""
persistence/queries/causal_queries.py — Queries for the causal graph

The most important query: validate that no cycles exist in the DAG.

Before inserting A→B, we verify that a path B→...→A does NOT exist.
This is done with a recursive CTE.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List


class CausalGraphQueries:
    """
    Specialized queries for the causal graph.

    All queries are async and return processed results.
    """

    @staticmethod
    async def check_causal_path_exists(
        session: AsyncSession,
        from_event_id: str,
        to_event_id: str
    ) -> bool:
        """
        Checks whether a causal path exists from from_event_id to to_event_id.

        Uses a recursive CTE to traverse the graph.

        This is the query that prevents cycles:
        Before inserting A→B, we call check_causal_path_exists(B, A).
        If it returns True, it means B→...→A already exists, and creating A→B
        would create a cycle.

        Args:
            session: SQLAlchemy async session.
            from_event_id: Starting event of the path.
            to_event_id: Target event we are trying to reach.

        Returns:
            True if a path exists, False otherwise.
        """
        query = text("""
            WITH RECURSIVE causal_path AS (
                -- Base case: start from from_event_id
                SELECT
                    cause_event_id,
                    effect_event_id,
                    1 AS depth
                FROM event_edges
                WHERE cause_event_id = :from_event_id

                UNION

                -- Recursive case: follow causal edges
                SELECT
                    e.cause_event_id,
                    e.effect_event_id,
                    p.depth + 1
                FROM event_edges e
                INNER JOIN causal_path p ON e.cause_event_id = p.effect_event_id
                WHERE p.depth < 100  -- Safety limit against infinite loops
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
        Returns all causal ancestors of an event.

        Ancestors = events that caused this one, directly or indirectly.

        Args:
            session: Async session.
            event_id: Event to find ancestors for.
            max_depth: Maximum search depth.

        Returns:
            List of ancestor event_ids, ordered by topo_order.
        """
        query = text("""
            WITH RECURSIVE ancestors AS (
                -- Base case: direct parents
                SELECT
                    e.cause_event_id AS ancestor_id,
                    1 AS depth
                FROM event_edges e
                WHERE e.effect_event_id = :event_id

                UNION

                -- Recursive case: traverse up the tree
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
        Returns all causal descendants of an event.

        Descendants = events caused by this one, directly or indirectly.

        Args:
            session: Async session.
            event_id: Event to find descendants for.
            max_depth: Maximum search depth.

        Returns:
            List of descendant event_ids.
        """
        query = text("""
            WITH RECURSIVE descendants AS (
                -- Base case: direct children
                SELECT
                    e.effect_event_id AS descendant_id,
                    1 AS depth
                FROM event_edges e
                WHERE e.cause_event_id = :event_id

                UNION

                -- Recursive case: traverse down the tree
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
        Returns all events in a world in topological order.

        Topological order: if A caused B, then A appears before B.

        This is useful for:
        - Reconstructing state from the beginning
        - Exporting the complete story
        - Validating that the DAG is coherent

        Args:
            session: Async session.
            world_id: World to get events for.

        Returns:
            List of event_ids in topological order.
        """
        query = text("""
            WITH RECURSIVE topo_sort AS (
                -- Base case: root events (no parents)
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

                -- Recursive case: events with all their parents already processed
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
        Statistics for the causal graph of a world.

        Useful for the paper and for debugging.

        Returns:
            Dict with: total_events, total_edges, avg_causes_per_event,
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
