"""
models/event.py — Events and the Causal Graph

A NarrativeEvent is the atomic unit of the engine.
Everything that happens in the story is an event: a battle,
a conversation, a death, a discovery.

Events connect to each other forming a DAG (Directed Acyclic Graph):
    king_death → civil_war → foreign_invasion

The DAG constraint (no cycles) is what guarantees that the story
is causally coherent: no event can be the cause of itself.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    """Types of events the engine can process."""
    DECISION    = "decision"     # Action taken by the player
    CONSEQUENCE = "consequence"  # Direct consequence of a decision
    FORCED      = "forced"       # Event forced by the DramaticEngine (thresholds)
    CLIMAX      = "climax"       # Forced narrative climax
    REVELATION  = "revelation"   # Mystery revelation
    ENDING      = "ending"       # End of the story


class CausalRelationType(str, Enum):
    """
    Type of causal relationship between two events.
    Useful for the paper and for the AI to understand the graph.
    """
    DIRECT      = "direct"       # A directly caused B
    ENABLES     = "enables"      # A made B possible
    TRIGGERS    = "triggers"     # A triggered B (with some delay)
    PREVENTS    = "prevents"     # A prevented C from happening (negative)
    AMPLIFIES   = "amplifies"    # A made B more intense


# ── State deltas ──────────────────────────────────────────────────────────────

@dataclass
class EntityDelta:
    """
    Represents the change in an attribute of an entity.

    Example: hero.health changes from 100 to 90.
        entity_id = "uuid-of-hero"
        attribute = "health"
        old_value = 100
        new_value = 90

    We store both old_value AND new_value so we can:
    - Reconstruct the state in any direction
    - Detect inconsistencies
    - Generate a readable history for the AI
    """
    entity_id:  str
    entity_name: str      # For readability in logs and AI context
    attribute:  str
    old_value:  Any
    new_value:  Any

    @property
    def delta_summary(self) -> str:
        """Readable summary to include in the AI context."""
        return f"{self.entity_name}.{self.attribute}: {self.old_value} → {self.new_value}"


@dataclass
class WorldVariableDelta:
    """
    Change in a global world variable.

    Example: political_stability drops from 60 to 45.
    """
    variable:  str
    old_value: Any
    new_value: Any

    @property
    def delta_summary(self) -> str:
        return f"world.{self.variable}: {self.old_value} → {self.new_value}"


@dataclass
class EntityCreation:
    """
    Represents the creation of a new entity during the story.

    Example: A mysterious stranger appears in chapter 3.
        entity_name = "Zara the Wanderer"
        entity_type = "character"
        attributes = {"health": 100, "loyalty": 50}
    """
    entity_name: str
    entity_type: str
    attributes: dict[str, Any] = field(default_factory=dict)
    entity_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def creation_summary(self) -> str:
        attrs_str = ", ".join(f"{k}={v}" for k, v in self.attributes.items())
        return f"NEW: {self.entity_name} ({self.entity_type}): {attrs_str}"


@dataclass
class DramaticDelta:
    """
    Change in the dramatic vector caused by this event.

    The DramaticEngine applies these deltas AFTER the event
    is validated and before the commit is persisted.
    """
    tension:    int = 0
    hope:       int = 0
    chaos:      int = 0
    rhythm:     int = 0
    saturation: int = 0
    connection: int = 0
    mystery:    int = 0

    def is_empty(self) -> bool:
        """Does this delta change nothing?"""
        return all(v == 0 for v in [
            self.tension, self.hope, self.chaos, self.rhythm,
            self.saturation, self.connection, self.mystery
        ])

    def to_dict(self) -> dict[str, int]:
        return {
            "tension": self.tension, "hope": self.hope,
            "chaos": self.chaos, "rhythm": self.rhythm,
            "saturation": self.saturation, "connection": self.connection,
            "mystery": self.mystery,
        }

    def __str__(self) -> str:
        parts = []
        fields = self.to_dict()
        for k, v in fields.items():
            if v != 0:
                sign = "+" if v > 0 else ""
                parts.append(f"{k}{sign}{v}")
        return ", ".join(parts) if parts else "no dramatic changes"


# ── NarrativeEvent ────────────────────────────────────────────────────────────

@dataclass
class NarrativeEvent:
    """
    The atomic unit of the narrative engine.

    An event represents something that happened in the story, with:
    - Its narrative (the text the player sees)
    - Its causes (which previous events made it possible)
    - Its effects (what changes in the world)
    - Its dramatic impact (how it moves the meters)

    Critical invariant: caused_by can only contain IDs of earlier
    events (lower depth). This guarantees the cycle-free DAG.
    """
    commit_id:       str           # Which narrative commit it belongs to
    event_type:      EventType
    narrative_text:  str           # The text the player sees
    summary:         str           # 1-sentence summary for the active trunk

    # Causal graph: IDs of the events that caused this one
    # If empty, this is an initial event (DAG root)
    caused_by:       list[str]     = field(default_factory=list)

    # Which player decision triggered it (None if forced)
    triggered_by_decision: str | None = None

    # Causal reason generated by the AI (why this event occurs)
    causal_reason: str | None = None

    # The effects of the event on the world
    entity_deltas:    list[EntityDelta]        = field(default_factory=list)
    entity_creations: list[EntityCreation]     = field(default_factory=list)
    world_deltas:     list[WorldVariableDelta] = field(default_factory=list)
    dramatic_delta:   DramaticDelta            = field(default_factory=DramaticDelta)

    # If this is a FORCED event, which meter triggered it
    forced_by_meter: str | None    = None

    # Metadata
    id:         str      = field(default_factory=lambda: str(uuid.uuid4()))
    depth:      int      = 0       # Narrative depth at which it occurred
    created_at: datetime = field(default_factory=datetime.now)

    # For the paper: topological order in the DAG
    # A child event always has topo_order > than its parents
    topo_order: int = 0

    def is_root(self) -> bool:
        """Is this a root event (no prior causes)?"""
        return len(self.caused_by) == 0

    def affects_entity(self, entity_id: str) -> bool:
        """Does this event modify the given entity?"""
        return any(d.entity_id == entity_id for d in self.entity_deltas)

    def get_summary_for_context(self) -> str:
        """
        Returns a compact representation to include in the active trunk.
        Distant events are compressed to this form to save tokens.
        """
        prefix = ""
        if self.triggered_by_decision:
            prefix = f'[Decision: "{self.triggered_by_decision}"] '
        elif self.forced_by_meter:
            prefix = f"[Forced event by {self.forced_by_meter}] "

        return f"• {prefix}{self.summary}"

    def __str__(self) -> str:
        return (
            f"NarrativeEvent(type={self.event_type.value}, "
            f"depth={self.depth}, "
            f"causes={len(self.caused_by)}, "
            f"drama={self.dramatic_delta})"
        )


# ── CausalEdge ────────────────────────────────────────────────────────────────

@dataclass
class CausalEdge:
    """
    An edge of the causal graph: event A caused event B.

    The CausalValidator uses these edges to detect cycles.
    Before creating an edge A->B, it verifies that there is NO
    path from B->A (which would create a cycle).

    For the paper: the relation_type allows analyzing the type of
    causality predominant in different narrative genres.
    """
    cause_event_id:  str    # The event that caused
    effect_event_id: str    # The event that was caused

    relation_type:   CausalRelationType = CausalRelationType.DIRECT
    strength:        float              = 1.0   # [0.0 - 1.0] causal strength

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __str__(self) -> str:
        return (
            f"CausalEdge({self.cause_event_id[:8]}... "
            f"→{self.relation_type.value}→ "
            f"{self.effect_event_id[:8]}...)"
        )
