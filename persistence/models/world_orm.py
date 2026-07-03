"""
persistence/models/world_orm.py — ORM for WorldDefinition and Entity

Maps:
- WorldDefinition → worlds table
- Entity → entities table
"""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean, JSON, ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any

from persistence.database import Base
from cne_core.models.world import EntityType, NarrativeTone


class WorldORM(Base):
    """
    Table: worlds

    Maps WorldDefinition (the world seed).
    """
    __tablename__ = "worlds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    protagonist: Mapped[str] = mapped_column(Text, nullable=False)
    era: Mapped[str] = mapped_column(String(200), nullable=False)
    tone: Mapped[str] = mapped_column(String(50), nullable=False)

    antagonist: Mapped[str] = mapped_column(Text, default="unknown")
    rules: Mapped[str] = mapped_column(Text, default="The world follows its own laws")
    constraints: Mapped[dict[str, Any]] = mapped_column(JSON, default=list)  # List of strings

    # Initial dramatic configuration (JSON containing the 7 meters)
    dramatic_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    max_depth: Mapped[int] = mapped_column(Integer, default=0)
    output_language: Mapped[str] = mapped_column(String(10), default="es")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relationships
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
        return f"<WorldORM(id={self.id[:8]}..., name='{self.name}', lang='{self.output_language}')>"


class EntityORM(Base):
    """
    Table: entities

    Maps Entity (characters, items, locations).

    Entities are NEVER deleted from the DB; they are only marked as destroyed
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

    # Dynamic attributes (JSON): {"health": 100, "loyalty": 80, ...}
    attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at_depth: Mapped[int] = mapped_column(Integer, default=0)
    destroyed_at_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relationships
    world: Mapped["WorldORM"] = relationship("WorldORM", back_populates="entities")

    @property
    def is_alive(self) -> bool:
        return self.destroyed_at_depth is None

    def __repr__(self) -> str:
        status = "✓" if self.is_alive else "✗"
        return f"<EntityORM([{status}] {self.name}, type={self.entity_type})>"
