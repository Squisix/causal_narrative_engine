"""
persistence/database.py — Configuración de SQLAlchemy 2.0 async

Define la base declarativa y la sesión async.
"""

from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from typing import AsyncGenerator
import os


class Base(DeclarativeBase):
    """
    Base declarativa para todos los ORM models.

    Todos los modelos heredan de esto:
        class WorldORM(Base):
            __tablename__ = "worlds"
            ...
    """
    pass


class DatabaseConfig:
    """
    Configuración y factory de sesiones async.

    Uso:
        config = DatabaseConfig("postgresql+asyncpg://user:pass@localhost/cne")
        async with config.get_session() as session:
            result = await session.execute(query)
    """

    def __init__(self, database_url: str, echo: bool = False):
        """
        Args:
            database_url: URL de conexión. Ejemplos:
                - PostgreSQL: "postgresql+asyncpg://user:pass@localhost/cne"
                - SQLite: "sqlite+aiosqlite:///./cne.db"
            echo: Si True, loguea todas las queries SQL (útil para debug).
        """
        self.engine = create_async_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True,     # Verifica conexiones antes de usarlas
            pool_size=10,           # Pool de conexiones
            max_overflow=20,
        )
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,  # No expira objetos después del commit
        )

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Context manager que retorna una sesión async.

        Uso:
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
        Crea todas las tablas definidas en los ORM models.

        SOLO usar en desarrollo/tests. En producción usar Alembic.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_all_tables(self) -> None:
        """
        Borra todas las tablas. SOLO usar en tests.
        """
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    async def dispose(self) -> None:
        """Cierra el engine y libera recursos."""
        await self.engine.dispose()


# ── Global Session Factory ────────────────────────────────────────────────────

# Engine global (singleton)
_global_engine = None
_global_session_maker = None


def get_engine():
    """Obtiene o crea el engine global."""
    global _global_engine, _global_session_maker

    if _global_engine is None:
        # Leer DATABASE_URL del entorno (seteado por .env)
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
    Dependency para FastAPI que retorna una sesión async.

    Maneja transacciones automáticamente:
    - Commit al finalizar exitosamente
    - Rollback en caso de excepción

    Uso en routers:
        @router.get("/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_session)):
            result = await session.execute(...)
    """
    # Asegurar que el engine esté creado
    get_engine()

    async with _global_session_maker() as session:
        try:
            yield session
            # Commit automático si todo salió bien
            await session.commit()
        except Exception:
            # Rollback en caso de error
            await session.rollback()
            raise
        finally:
            # Cerrar la sesión
            await session.close()
