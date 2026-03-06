"""
persistence/models/commit_orm.py — ORM para commits y estado dramático

Mapea:
- NarrativeCommit → tabla commits
- Branch → tabla branches
- DramaticVector → tabla dramatic_states
- DramaticDelta (histórico) → tabla dramatic_deltas
"""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, JSON, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any

from persistence.database import Base


class CommitORM(Base):
    """
    Tabla: commits

    Mapea NarrativeCommit (el árbol versionado de decisiones).
    """
    __tablename__ = "commits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    world_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False
    )
    branch_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("branches.id", ondelete="SET NULL"),
        nullable=True
    )

    # Parent commit (None solo en el commit raíz)
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("commits.id", ondelete="SET NULL"),
        nullable=True
    )

    # Decisión tomada (None en el commit inicial)
    choice_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Narrativa
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Metadata narrativa
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    is_ending: Mapped[bool] = mapped_column(Boolean, default=False)

    # Snapshots ligeros (JSON)
    # En Fase 2 completa, estos se reemplazarán por state_rebuilder
    world_state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    entity_states_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    world: Mapped["WorldORM"] = relationship("WorldORM", back_populates="commits")
    branch: Mapped["BranchORM | None"] = relationship("BranchORM", back_populates="commits")

    # Eventos asociados a este commit
    events: Mapped[list["EventORM"]] = relationship(
        "EventORM",
        back_populates="commit",
        cascade="all, delete-orphan"
    )

    # Estado dramático en este commit
    dramatic_state: Mapped["DramaticStateORM | None"] = relationship(
        "DramaticStateORM",
        back_populates="commit",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Commits hijos (para navegación del árbol)
    # Self-referential relationship: parent_id → id
    children: Mapped[list["CommitORM"]] = relationship(
        "CommitORM",
        foreign_keys="[CommitORM.parent_id]",
        back_populates="parent"
    )
    parent: Mapped["CommitORM | None"] = relationship(
        "CommitORM",
        foreign_keys="[CommitORM.parent_id]",
        remote_side="[CommitORM.id]",
        back_populates="children"
    )

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    def __repr__(self) -> str:
        choice = f'"{self.choice_text}"' if self.choice_text else "inicio"
        return f"<CommitORM(id={self.id[:8]}..., depth={self.depth}, choice={choice})>"


class BranchORM(Base):
    """
    Tabla: branches

    Mapea Branch (metadata de ramas del árbol narrativo).
    """
    __tablename__ = "branches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    world_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("worlds.id", ondelete="CASCADE"),
        nullable=False
    )

    origin_commit_id: Mapped[str] = mapped_column(String(36), nullable=False)
    leaf_commit_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    name: Mapped[str] = mapped_column(String(200), default="Rama principal")
    description: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    commits: Mapped[list["CommitORM"]] = relationship("CommitORM", back_populates="branch")

    def __repr__(self) -> str:
        return f"<BranchORM(id={self.id[:8]}..., name='{self.name}')>"


class DramaticStateORM(Base):
    """
    Tabla: dramatic_states

    Mapea el estado del DramaticVector en un commit.

    Uno por commit. Almacena los 7 medidores + metadata de eventos forzados.
    """
    __tablename__ = "dramatic_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    commit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("commits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True   # Un estado dramático por commit
    )

    # Los 7 medidores del SDMM
    tension: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=30
    )
    hope: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=60
    )
    chaos: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=20
    )
    rhythm: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=50
    )
    saturation: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=0
    )
    connection: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=40
    )
    mystery: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        default=50
    )

    # Metadata de evento forzado (si aplica)
    forced_event: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trigger_meter: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    commit: Mapped["CommitORM"] = relationship("CommitORM", back_populates="dramatic_state")

    def to_dict(self) -> dict[str, int]:
        return {
            "tension": self.tension,
            "hope": self.hope,
            "chaos": self.chaos,
            "rhythm": self.rhythm,
            "saturation": self.saturation,
            "connection": self.connection,
            "mystery": self.mystery,
        }

    def __repr__(self) -> str:
        return (
            f"<DramaticStateORM(commit={self.commit_id[:8]}..., "
            f"T={self.tension}, H={self.hope}, C={self.chaos})>"
        )


class DramaticDeltaORM(Base):
    """
    Tabla: dramatic_deltas

    Historial de cambios en medidores dramáticos.

    Esto NO es necesario para el funcionamiento del motor, pero sí
    para el paper: permite analizar qué eventos afectan más cada medidor.
    """
    __tablename__ = "dramatic_deltas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )

    meter: Mapped[str] = mapped_column(String(50), nullable=False)
    delta: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    def __repr__(self) -> str:
        sign = "+" if self.delta > 0 else ""
        return f"<DramaticDeltaORM({self.meter}{sign}{self.delta})>"
