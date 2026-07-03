"""
persistence/repositories — NarrativeRepository implementations

- PostgreSQLRepository: Production with PostgreSQL
- SQLiteRepository: Local development without Docker
- InMemoryRepository: Tests without dependencies (already exists in Phase 1)
"""

from persistence.repositories.postgresql_repository import PostgreSQLRepository

__all__ = ["PostgreSQLRepository"]
