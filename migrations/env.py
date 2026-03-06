"""
migrations/env.py — Configuración del entorno de Alembic

Adaptado para SQLAlchemy 2.0 async.
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Importar la Base declarativa y todos los modelos ORM
from persistence.database import Base
from persistence.models.world_orm import WorldORM, EntityORM
from persistence.models.event_orm import EventORM, CausalEdgeORM, EntityDeltaORM, WorldVariableDeltaORM
from persistence.models.commit_orm import CommitORM, BranchORM, DramaticStateORM, DramaticDeltaORM

# Configuración de Alembic
config = context.config

# Configurar logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Ejecutar migraciones en modo 'offline'.

    Genera SQL sin conectarse a la DB.
    Útil para generar scripts SQL para ejecutar manualmente.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Helper para ejecutar migraciones con una conexión."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Ejecutar migraciones en modo async.

    Esto es necesario porque usamos asyncpg.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = config.get_main_option("sqlalchemy.url")

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Ejecutar migraciones en modo 'online'.

    Se conecta a la DB y ejecuta las migraciones.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
