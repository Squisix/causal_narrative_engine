"""
persistence/database.py — SQLAlchemy 2.0 async configuration

Defines the declarative base and async session.
"""

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import os


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.

    All models inherit from this:
        class WorldORM(Base):
            __tablename__ = "worlds"
            ...
    """
    pass


class DatabaseConfig:
    """
    Configuration and async session factory.

    Usage:
        config = DatabaseConfig("postgresql+asyncpg://user:pass@localhost/cne")
        async with config.get_session() as session:
            result = await session.execute(query)
    """

    def __init__(self, database_url: str, echo: bool = False):
        """
        Args:
            database_url: Connection URL. Examples:
                - PostgreSQL: "postgresql+asyncpg://user:pass@localhost/cne"
                - SQLite: "sqlite+aiosqlite:///./cne.db"
            echo: If True, logs all SQL queries (useful for debug).
        """
        self.engine = create_async_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,     # Verify connections before using them
            pool_size=10,           # Connection pool
            max_overflow=20,
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Do not expire objects after commit
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager that returns an async session.

        Usage:
            async with config.get_session() as session:
                await session.execute(...)
                await session.commit()
        """
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def create_all_tables(self) -> None:
        """
        Creates all tables defined in the ORM models.

        Only use in development/tests. In production use Alembic.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all_tables(self) -> None:
        """
        Drops all tables. Only use in tests.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def dispose(self) -> None:
        """Closes the engine and releases resources."""
        await self.engine.dispose()


# ── Global Session Factory ────────────────────────────────────────────────────

# Global engine (singleton)
_global_engine = None
_global_session_maker = None


def get_engine():
    """Gets or creates the global engine."""
    global _global_engine, _global_session_maker

    if _global_engine is None:
        # Read DATABASE_URL from environment (set by .env)
        database_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://cne_user:cne_password@localhost:5433/cne_db"
        )

        _global_engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )

        _global_session_maker = async_sessionmaker(
            _global_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    return _global_engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that returns an async session.

    Handles transactions automatically:
    - Commits on successful completion
    - Rolls back on exception

    Usage in routers:
        @router.get("/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            result = await session.execute(...)
    """
    # Ensure the engine is created
    get_engine()

    async with _global_session_maker() as session:
        try:
            yield session
            # Auto-commit if everything went well
            await session.commit()
        except Exception:
            # Rollback on error
            await session.rollback()
            raise
        finally:
            # Close the session
            await session.close()
