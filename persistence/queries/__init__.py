"""
persistence/queries — Queries complejas SQL

Queries que requieren CTEs recursivas, subqueries, o lógica avanzada.
"""

from persistence.queries.causal_queries import CausalGraphQueries

__all__ = ["CausalGraphQueries"]
