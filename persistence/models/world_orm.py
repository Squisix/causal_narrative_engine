"""
persistence/models/world_orm.py — ORM para WorldDefinition y Entity

Mapea:
- WorldDefinition → tabla worlds
- Entity → tabla entities
"""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any

from persistence.database import Base
from cne_core.models.world import EntityType, NarrativeTone


class WorldORM(Base):
    """
    Tabla: worlds

    Mapea WorldDefinition (la semilla del mundo).
    """
    __tablename__ = "worlds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    protagonist: Mapped[str] = mapped_column(Text, nullable=False)
    era: Mapped[str] = mapped_column(String(200), nullable=False)
    tone: Mapped[str] = mapped_column(String(50), nullable=False)

    antagonist: Mapped[str] = mapped_column(Text, default="desconocido")
    rules: Mapped[str] = mapped_column(Text, default="El mundo sigue sus propias leyes")
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=list)  # Lista de strings

    # Configuración dramática inicial (JSON con los 7 medidores)
    dramatic_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    max_depth: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    entities: Mapped[list["EntityORM"]] = relationship(
        "EntityORM",
        back_populates="world",
        cascade="all, delete-orphan"
    )
    commits: Mapped[list["CommitORM"]] = relationship(
        "CommitORM",
        back_populates="world",
        cascade="all, delete-orphan",
        foreign_keys="CommitORM.world_id"
    )

    def __repr__(self) -> str:
        return f"<WorldORM(id={self.id[:8]}..., name='{self.name}')>"


class EntityORM(Base):
    """
    Tabla: entities

    Mapea Entity (personajes, objetos, locaciones).

    Las entidades NUNCA se borran, solo se marcan como destruidas
    (destroyed_at_depth IS NOT NULL).
    """
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    world_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Atributos dinámicos (JSON): {"health": 100, "loyalty": 80, ...}
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at_depth: Mapped[int] = mapped_column(Integer, default=0)
    destroyed_at_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    world: Mapped["WorldORM"] = relationship("WorldORM", back_populates="entities")

    @property
    def is_alive(self) -> bool:
        return self.destroyed_at_depth is None

    def __repr__(self) -> str:
        status = "✓" if self.is_alive else "✗"
        return f"<EntityORM([{status}] {self.name}, type={self.entity_type})>"
