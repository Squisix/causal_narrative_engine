"""
persistence/repositories — Implementaciones de NarrativeRepository

- PostgreSQLRepository: Producción con PostgreSQL
- SQLiteRepository: Desarrollo local sin Docker
- InMemoryRepository: Tests sin dependencias (ya existe en Fase 1)
"""

from persistence.repositories.postgresql_repository import PostgreSQLRepository

__all__ = ["PostgreSQLRepository"]
