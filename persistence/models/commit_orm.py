"""
persistence/models/commit_orm.py — ORM for commits and dramatic state

Maps:
- NarrativeCommit → commits table
- Branch → branches table
- DramaticVector → dramatic_states table
- DramaticDelta (history) → dramatic_deltas table
"""

from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, Boolean, ForeignKey, JSON, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Any

from persistence.database import Base


class CommitORM(Base):
    """
    Table: commits

    Maps NarrativeCommit (the versioned decision tree).
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

    # Parent commit (None only for the root commit)
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("commits.id", ondelete="SET NULL"),
        nullable=True
    )

    # Decision taken (None for the initial commit)
    choice_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Narrative
    narrative_text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)

    # Narrative metadata
    depth: Mapped[int] = mapped_column(Integer, nullable=False)
    is_ending: Mapped[bool] = mapped_column(Boolean, default=False)

    # Lightweight snapshots (JSON)
    # In the full Phase 2, these will be replaced by state_rebuilder
    world_state_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    entity_states_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relationships
    world: Mapped["WorldORM"] = relationship("WorldORM", back_populates="commits")
    branch: Mapped["BranchORM | None"] = relationship("BranchORM", back_populates="commits")

    # Events associated with this commit
    events: Mapped[list["EventORM"]] = relationship(
        "EventORM",
        back_populates="commit",
        cascade="all, delete-orphan"
    )

    # Dramatic state at this commit
    dramatic_state: Mapped["DramaticStateORM | None"] = relationship(
        "DramaticStateORM",
        back_populates="commit",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # Choices available to the player at this commit
    choices: Mapped[list["ChoiceORM"]] = relationship(
        "ChoiceORM",
        back_populates="commit",
        cascade="all, delete-orphan",
        order_by="ChoiceORM.display_order"
    )

    # Child commits (for tree navigation)
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
        choice = f'"{self.choice_text}"' if self.choice_text else "beginning"
        return f"<CommitORM(id={self.id[:8]}..., depth={self.depth}, choice={choice})>"


class BranchORM(Base):
    """
    Table: branches

    Maps Branch (metadata for narrative tree branches).
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

    name: Mapped[str] = mapped_column(String(200), default="Main branch")
    description: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relationships
    commits: Mapped[list["CommitORM"]] = relationship("CommitORM", back_populates="branch")

    def __repr__(self) -> str:
        return f"<BranchORM(id={self.id[:8]}..., name='{self.name}')>"


class DramaticStateORM(Base):
    """
    Table: dramatic_states

    Maps the DramaticVector state at a commit.

    One per commit. Stores the 7 meters + forced event metadata.
    """
    __tablename__ = "dramatic_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)

    commit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("commits.id", ondelete="CASCADE"),
        nullable=False,
        unique=True   # One dramatic state per commit
    )

    # The 7 SDMM meters
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

    # Forced event metadata (if applicable)
    forced_event: Mapped[str | None] = mapped_column(String(50), nullable=True)
    trigger_meter: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relationships
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
    Table: dramatic_deltas

    History of changes in dramatic meters.

    This is NOT necessary for engine operation, but it is
    for the paper: it allows analyzing which events affect each meter most.
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


class ChoiceORM(Base):
    """
    Table: choices

    Maps NarrativeChoice. Options available to the player at each commit.
    """
    __tablename__ = "choices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    commit_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("commits.id", ondelete="CASCADE"),
        nullable=False
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    tone_hint: Mapped[str] = mapped_column(String(100), default="")
    estimated_depth_until_ending: Mapped[int | None] = mapped_column(Integer, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)

    # Relationships
    commit: Mapped["CommitORM"] = relationship("CommitORM", back_populates="choices")

    def __repr__(self) -> str:
        return f"<ChoiceORM(commit={self.commit_id[:8]}..., text='{self.text[:30]}...')>"
