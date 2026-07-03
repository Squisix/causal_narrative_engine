"""
persistence/queries — Complex SQL queries

Queries that require recursive CTEs, subqueries, or advanced logic.
"""

from persistence.queries.causal_queries import CausalGraphQueries

__all__ = ["CausalGraphQueries"]
