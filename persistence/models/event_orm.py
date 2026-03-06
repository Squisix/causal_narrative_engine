"""
persistence/models/event_orm.py — ORM para eventos y grafo causal

Mapea:
- NarrativeEvent → tabla events
- CausalEdge → tabla event_edges (el DAG)
- EntityDelta → tabla entity_deltas
- WorldVariableDelta → tabla world_variable_deltas
"""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any

from persistence.database import Base


class EventORM(Base):
    """
    Tabla: events

    Mapea NarrativeEvent (la unidad atómica del motor).
    """
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    commit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("commits.id", ondelete="CASCADE"),
        nullable=False
    )

    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Decisión que disparó este evento (None si fue forzado)
    triggered_by_decision: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Si es un evento FORCED, qué medidor lo disparó
    forced_by_meter: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Metadata narrativa
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    topo_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    commit: Mapped["CommitORM"] = relationship("CommitORM", back_populates="events")

    # Aristas causales SALIENTES (este evento causó otros)
    causal_children: Mapped[list["CausalEdgeORM"]] = relationship(
        "CausalEdgeORM",
        foreign_keys="CausalEdgeORM.cause_event_id",
        back_populates="cause_event",
        cascade="all, delete-orphan"
    )

    # Aristas causales ENTRANTES (otros eventos causaron este)
    causal_parents: Mapped[list["CausalEdgeORM"]] = relationship(
        "CausalEdgeORM",
        foreign_keys="CausalEdgeORM.effect_event_id",
        back_populates="effect_event",
        cascade="all, delete-orphan"
    )

    entity_deltas: Mapped[list["EntityDeltaORM"]] = relationship(
        "EntityDeltaORM",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    world_deltas: Mapped[list["WorldVariableDeltaORM"]] = relationship(
        "WorldVariableDeltaORM",
        back_populates="event",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<EventORM(id={self.id[:8]}..., type={self.event_type}, depth={self.depth})>"


class CausalEdgeORM(Base):
    """
    Tabla: event_edges

    Mapea CausalEdge. Representa el DAG causal: A → B.

    CONSTRAINT crítico: antes de insertar A→B, verificar que NO exista B→...→A
    (eso se hace con la CTE recursiva en queries/causal_queries.py).
    """
    __tablename__ = "event_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    cause_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )
    effect_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )

    relation_type: Mapped[str] = mapped_column(String(50), default="direct")
    strength: Mapped[float] = mapped_column(Float, default=1.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    cause_event: Mapped["EventORM"] = relationship(
        "EventORM",
        foreign_keys=[cause_event_id],
        back_populates="causal_children"
    )
    effect_event: Mapped["EventORM"] = relationship(
        "EventORM",
        foreign_keys=[effect_event_id],
        back_populates="causal_parents"
    )

    def __repr__(self) -> str:
        return (
            f"<CausalEdgeORM({self.cause_event_id[:8]}... "
            f"→{self.relation_type}→ "
            f"{self.effect_event_id[:8]}...)>"
        )


class EntityDeltaORM(Base):
    """
    Tabla: entity_deltas

    Mapea EntityDelta. Registra cambios en atributos de entidades.
    """
    __tablename__ = "entity_deltas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )
    entity_id: Mapped[str] = mapped_column(String(36), nullable=False)
    entity_name: Mapped[str] = mapped_column(String(200), nullable=False)

    attribute: Mapped[str] = mapped_column(String(100), nullable=False)

    # old_value y new_value son JSON porque pueden ser cualquier tipo
    old_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    event: Mapped["EventORM"] = relationship("EventORM", back_populates="entity_deltas")

    def __repr__(self) -> str:
        return (
            f"<EntityDeltaORM({self.entity_name}.{self.attribute}: "
            f"{self.old_value} → {self.new_value})>"
        )


class WorldVariableDeltaORM(Base):
    """
    Tabla: world_variable_deltas

    Mapea WorldVariableDelta. Registra cambios en variables globales del mundo.
    """
    __tablename__ = "world_variable_deltas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False
    )

    variable: Mapped[str] = mapped_column(String(100), nullable=False)

    old_value: Mapped[Any] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Any] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relaciones
    event: Mapped["EventORM"] = relationship("EventORM", back_populates="world_deltas")

    def __repr__(self) -> str:
        return (
            f"<WorldVariableDeltaORM(world.{self.variable}: "
            f"{self.old_value} → {self.new_value})>"
        )
