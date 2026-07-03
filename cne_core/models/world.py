"""
models/world.py — The Seed of the Literary Tree

In Python, @dataclass automatically generates __init__, __repr__, and __eq__
from the defined fields. It is equivalent to a 'data class' in Kotlin, 
a 'record' in Java 17+, or a 'struct' in Go.

field(default_factory=...) is used for default values of mutable objects 
(lists, dicts). In Python, never assign [] or {} directly as a default 
value in a dataclass — it would be shared among all instances.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    """
    str + Enum: the value is a string, which makes it directly JSON serializable.
    Useful when persisting or sending data to the AI.
    """
    CHARACTER = "character"
    FACTION   = "faction"
    ARTIFACT  = "artifact"
    LOCATION  = "location"


class NarrativeTone(str, Enum):
    """Supported narrative tones for story generation."""
    EPIC          = "epic"
    DARK          = "dark"
    MYSTERIOUS    = "mysterious"
    ADVENTUROUS   = "adventurous"
    PHILOSOPHICAL = "philosophical"
    BLACK_HUMOR   = "black_humor"


# ── Entity ────────────────────────────────────────────────────────────────────

@dataclass
class Entity:
    """
    A persistent entity in the narrative world.

    The engine NEVER deletes entities — it only marks them as destroyed.
    This preserves the complete history and allows reconstructing any past state.

    Attributes:
        id:                 Unique identifier. uuid4() generates a random one.
        name:               Name of the character, object, or location.
        entity_type:        Type of entity (see EntityType).
        attributes:         Flexible dictionary for any world attribute.
                            E.g., {"alive": True, "health": 100, "loyalty": 80}
        created_at_depth:   Narrative depth at which it was created.
        destroyed_at_depth: None if active, or narrative depth if destroyed.
    """
    name:        str
    entity_type: EntityType
    attributes:  dict[str, Any]       = field(default_factory=dict)
    id:          str                  = field(default_factory=lambda: str(uuid.uuid4()))
    created_at_depth:    int          = 0
    destroyed_at_depth:  int | None   = None   # None = active/alive

    @property
    def is_alive(self) -> bool:
        """
        A property in Python is a method accessed like an attribute.
        entity.is_alive  →  automatically calls this getter.
        """
        return self.destroyed_at_depth is None

    def get_attr(self, key: str, default: Any = None) -> Any:
        """Safe access to attributes with a default fallback."""
        return self.attributes.get(key, default)

    def __str__(self) -> str:
        status = "✓" if self.is_alive else "✗"
        return f"[{status}] {self.name} ({self.entity_type.value})"


# ── WorldDefinition (The Seed) ──────────────────────────────────────────────

@dataclass
class WorldDefinition:
    """
    The Seed — immutable once created.

    Defines the state space of possible stories. The AI always receives 
    this definition as part of the context. The rules defined here represent 
    the 'narrative contract' which neither the AI nor the player can violate.

    Attributes:
        name:               Name of the world/story.
        context:            Detailed description of the narrative universe.
        protagonist:        Name and description of the main character.
        era:                Era/setting (e.g., "Medieval fantasy, year 843").
        tone:               Overall narrative tone.
        antagonist:         Central conflict or antagonist.
        rules:              World rules (e.g., "Magic exists but has a blood price").
        constraints:        List of narratively FORBIDDEN occurrences.
                            Both the engine and the AI must respect these constraints.
        initial_entities:   Characters, objects, or locations existing from the start.
        dramatic_config:    Initial settings of the dramatic vector.
        max_depth:          Maximum narrative depth before forcing an ending (0 = unlimited).
        output_language:    The target language for generated narratives (e.g., 'es', 'en').
        id:                 Automatically generated UUID.
        created_at:         Creation timestamp.
    """
    name:       str
    context:    str
    protagonist: str
    era:        str
    tone:       NarrativeTone

    antagonist:  str              = "unknown"
    rules:       str              = "The world follows its own laws"
    constraints: list[str]        = field(default_factory=list)

    # Initial world entities
    initial_entities: list[Entity] = field(default_factory=list)

    # Dramatic configuration: initial values for each meter [0-100]
    # The engine uses this as the starting point for the DramaticVector
    dramatic_config: dict[str, int] = field(default_factory=lambda: {
        "tension":    30,
        "hope":       60,
        "chaos":      20,
        "rhythm":     50,
        "saturation": 0,
        "connection": 40,
        "mystery":    50,
    })

    max_depth: int  = 0   # 0 = no limit
    output_language: str = "es"

    id:         str       = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime  = field(default_factory=datetime.now)

    def get_entity_by_name(self, name: str) -> Entity | None:
        """Search an initial entity by name. Returns None if not found."""
        for entity in self.initial_entities:
            if entity.name.lower() == name.lower():
                return entity
        return None

    def to_context_string(self) -> str:
        """
        Serializes the seed to text for sending to the AI.
        This block is always present in the active context trunk.
        """
        lines = [
            f"WORLD: {self.name}",
            f"CONTEXT: {self.context}",
            f"PROTAGONIST: {self.protagonist}",
            f"ERA: {self.era}",
            f"TONE: {self.tone.value}",
            f"ANTAGONIST/CONFLICT: {self.antagonist}",
            f"WORLD RULES: {self.rules}",
            f"OUTPUT LANGUAGE: {self.output_language}",
        ]

        if self.constraints:
            lines.append("ABSOLUTE CONSTRAINTS:")
            for c in self.constraints:
                lines.append(f"  - {c}")

        if self.initial_entities:
            lines.append("INITIAL ENTITIES:")
            for e in self.initial_entities:
                attrs_str = ", ".join(f"{k}={v}" for k, v in e.attributes.items())
                lines.append(f"  - {e.name} ({e.entity_type.value}): {attrs_str}")

        return "\n".join(lines)

    def __str__(self) -> str:
        return f"WorldDefinition('{self.name}', tone={self.tone.value}, entities={len(self.initial_entities)}, lang={self.output_language})"
