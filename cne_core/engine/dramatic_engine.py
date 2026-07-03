"""
engine/dramatic_engine.py — The Multi-Meter Dramatic System (MMDS)

This module implements the Φ function of the formal model:
    Φ(D(t)) → forced event constraint (or None)

The DramaticEngine maintains the dramatic vector of 7 meters
and evaluates whether any has crossed a threshold that requires forcing
a specific event type.

The innovative key: when the engine forces an event (e.g., CLIMAX
because tension > 85), that event is NOT an external disruption.
It is integrated causally into the DAG: it has formal causes in all
the events that raised the tension up to that point.
"""

from dataclasses import dataclass, field
from enum import Enum


# ── Forced Event Types ────────────────────────────────────────────────────────

class ForcedEventType(str, Enum):
    """
    Types of events that the engine can force when a meter
    crosses its threshold. The AI must respect this constraint.
    """
    CLIMAX              = "CLIMAX"              # Tension > 85
    DISRUPTIVE          = "DISRUPTIVE"          # Tension < 15
    TRAGEDY             = "TRAGEDY"             # Hope < 10
    UNEXPECTED_THREAT   = "UNEXPECTED_THREAT"   # Hope > 90
    PLOT_TWIST          = "PLOT_TWIST"          # Saturation > 85
    ARC_CLOSURE         = "ARC_CLOSURE"         # Saturation > 95
    CHAOS_STORM         = "CHAOS_STORM"         # Chaos > 80
    NARRATIVE_REST      = "NARRATIVE_REST"      # Rhythm > 90 for 3 turns
    CLIMAX_REVELATION   = "CLIMAX_REVELATION"   # Mystery > 65 AND Tension > 65
    EMOTIONAL_MOMENT    = "EMOTIONAL_MOMENT"    # Connection > 70 AND Tension > 60


@dataclass
class ForcedEventConstraint:
    """
    The constraint that the engine passes to the AI when an event is forced.

    The AI receives this in the system prompt and MUST generate a narrative
    that corresponds to the forced event type.
    """
    event_type:    ForcedEventType
    trigger_meter: str     # What meter triggered it
    trigger_value: int     # Value of the triggering meter
    description:   str     # Clear instruction for the AI

    def to_prompt_constraint(self) -> str:
        """Text to include in the AI prompt."""
        return (
            f"⚠️ MANDATORY DRAMATIC CONSTRAINT: {self.description}\n"
            f"Required event type: {self.event_type.value}\n"
            f"Triggered by: {self.trigger_meter} = {self.trigger_value}\n"
            f"The generated narrative MUST reflect this dramatic moment. "
            f"It cannot be ignored or postponed."
        )


# ── DramaticVector ────────────────────────────────────────────────────────────

@dataclass
class DramaticVector:
    """
    The dramatic state vector D(t).

    7 meters that capture the emotional and structural state
    of the story at a given moment. All in the range [0, 100].

    The engine updates them after each event:
    1. Applies the event's DramaticDelta
    2. Applies interactions between meters
    3. Clamps all values to [0, 100]
    4. Evaluates thresholds → ForcedEventConstraint or None
    """
    tension:    int = 30
    hope:       int = 60
    chaos:      int = 20
    rhythm:     int = 50
    saturation: int = 0
    connection: int = 40
    mystery:    int = 50

    # Counter of turns with high rhythm (for the rest threshold)
    _high_rhythm_turns: int = field(default=0, repr=False)

    def apply_delta(self, delta: "DramaticDelta") -> None:
        """
        Applies a delta to the vector and then the interactions between meters.

        The order matters:
        1. Apply the event's direct delta
        2. Apply causal interactions between meters
        3. Clamp to [0, 100]
        """
        # 1. Apply direct delta
        self.tension    = self.tension    + delta.tension
        self.hope       = self.hope       + delta.hope
        self.chaos      = self.chaos      + delta.chaos
        self.rhythm     = self.rhythm     + delta.rhythm
        self.saturation = self.saturation + delta.saturation
        self.connection = self.connection + delta.connection
        self.mystery    = self.mystery    + delta.mystery

        # 2. Apply interactions between meters
        self._apply_interactions(delta)

        # 3. Clamp to valid range
        self._clamp()

        # 4. Update high rhythm turn counter
        if self.rhythm > 70:
            self._high_rhythm_turns += 1
        else:
            self._high_rhythm_turns = 0

    def _apply_interactions(self, delta: "DramaticDelta") -> None:
        """
        Causal interactions between meters.

        These are the relationships that make the system coherent with
        dramatic theory. They are applied AFTER the direct delta.
        """
        # High tension erodes hope
        # For every 10 points of tension > 50, hope drops by -2
        if self.tension > 50:
            hope_erosion = ((self.tension - 50) // 10) * 2
            self.hope -= hope_erosion

        # High chaos accelerates rhythm
        if self.chaos > 60:
            rhythm_boost = (self.chaos - 60) // 10
            self.rhythm += rhythm_boost

        # High saturation disconnects emotionally
        if self.saturation > 70:
            connection_loss = (self.saturation - 70) // 5
            self.connection -= connection_loss

        # Very low hope increases mystery (what is happening?)
        if self.hope < 20:
            self.mystery += 3

        # High connection amplifies the impact of tension
        # (does not modify the vector, but affects how thresholds are evaluated)
        # → see evaluate_thresholds()


    def _clamp(self) -> None:
        """Clamps all values in [0, 100]."""
        self.tension    = max(0, min(100, self.tension))
        self.hope       = max(0, min(100, self.hope))
        self.chaos      = max(0, min(100, self.chaos))
        self.rhythm     = max(0, min(100, self.rhythm))
        self.saturation = max(0, min(100, self.saturation))
        self.connection = max(0, min(100, self.connection))
        self.mystery    = max(0, min(100, self.mystery))

    def to_dict(self) -> dict[str, int]:
        """Serializes for persistence and AI context."""
        return {
            "tension": self.tension, "hope": self.hope,
            "chaos": self.chaos, "rhythm": self.rhythm,
            "saturation": self.saturation, "connection": self.connection,
            "mystery": self.mystery,
        }

    def from_dict(self, d: dict[str, int]) -> None:
        """Restores the vector from a dict (when loading a commit)."""
        self.tension    = d.get("tension", 30)
        self.hope       = d.get("hope", 60)
        self.chaos      = d.get("chaos", 20)
        self.rhythm     = d.get("rhythm", 50)
        self.saturation = d.get("saturation", 0)
        self.connection = d.get("connection", 40)
        self.mystery    = d.get("mystery", 50)

    def __str__(self) -> str:
        return (
            f"DramaticVector("
            f"T={self.tension} H={self.hope} C={self.chaos} "
            f"R={self.rhythm} S={self.saturation} "
            f"Con={self.connection} M={self.mystery})"
        )


# ── DramaticEngine ────────────────────────────────────────────────────────────

# We need to import DramaticDelta here but it is in models/event.py
# We use TYPE_CHECKING to avoid circular import at runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cne_core.models.event import DramaticDelta


class DramaticEngine:
    """
    The Φ function of the formal model: evaluates the dramatic vector
    and determines if an event should be forced.

    Typical usage:
        engine = DramaticEngine(world_def.dramatic_config)

        # After each player decision:
        engine.apply_delta(event.dramatic_delta)
        constraint = engine.evaluate_thresholds()

        if constraint:
            # Pass constraint to the AI as a mandatory instruction
            prompt = build_prompt(..., forced_constraint=constraint)
        else:
            prompt = build_prompt(...)
    """

    def __init__(self, initial_config: dict[str, int] | None = None):
        """
        Args:
            initial_config: Initial values of the vector from WorldDefinition.
                           If None, uses defaults from DramaticVector.
        """
        self.vector = DramaticVector()

        if initial_config:
            self.vector.from_dict(initial_config)

        # Meter history for analysis (paper)
        self._history: list[dict[str, int]] = [self.vector.to_dict()]

    @property
    def current_state(self) -> dict[str, int]:
        return self.vector.to_dict()

    def apply_delta_from_dict(self, delta_dict: dict[str, int]) -> None:
        """
        Applies a delta received as a dict (from the AI response).
        Creates a DramaticDelta and applies it to the vector.
        """
        from cne_core.models.event import DramaticDelta
        delta = DramaticDelta(
            tension    = delta_dict.get("tension", 0),
            hope       = delta_dict.get("hope", 0),
            chaos      = delta_dict.get("chaos", 0),
            rhythm     = delta_dict.get("rhythm", 0),
            saturation = delta_dict.get("saturation", 0),
            connection = delta_dict.get("connection", 0),
            mystery    = delta_dict.get("mystery", 0),
        )
        self.apply_delta(delta)

    def apply_delta(self, delta: "DramaticDelta") -> None:
        """Applies a DramaticDelta to the vector and saves in history."""
        self.vector.apply_delta(delta)
        self._history.append(self.vector.to_dict())

    def evaluate_thresholds(self) -> ForcedEventConstraint | None:
        """
        Φ: evaluates if any meter has crossed a threshold.

        The thresholds are evaluated in order of priority. If multiple
        thresholds are crossed, only the one with the highest priority is reported.

        Returns:
            ForcedEventConstraint if a threshold is crossed,
            None if the story can continue freely.
        """
        v = self.vector

        # Calculate consecutive turns with high tension (> 80) from session history
        high_tension_turns = 0
        for state in reversed(self._history):
            if state.get("tension", 0) > 80:
                high_tension_turns += 1
            else:
                break

        # Calculate consecutive turns with high chaos (> 75) from session history
        high_chaos_turns = 0
        for state in reversed(self._history):
            if state.get("chaos", 0) > 75:
                high_chaos_turns += 1
            else:
                break

        # ── Priority 1: Combinations of two meters ────────────────────────────
        # These conditions have higher precedence because they are more specific

        # Revelation Climax: high mystery + high tension
        if v.mystery > 65 and v.tension > 65:
            if high_tension_turns <= 2:
                description = (
                    f"The central mystery MUST be revealed now, at the moment of peak tension "
                    f"(Turn {high_tension_turns} of Climax). An ignored truth comes to light. "
                    f"Keep the dramatic intensity extremely high and the conflict active."
                )
            else:
                description = (
                    f"Tension and mystery have been at extreme levels for {high_tension_turns} chapters. "
                    f"The climax has reached its natural exhaustion threshold. You MUST initiate the "
                    f"resolution/decompression phase of this scene in your narrative. Furthermore, you are "
                    f"required to return significantly negative dramatic_deltas for 'mystery' (between -20 and -40) "
                    f"and 'tension' (between -20 and -35) to cool down the dramatic state and let the story advance."
                )

            return ForcedEventConstraint(
                event_type    = ForcedEventType.CLIMAX_REVELATION,
                trigger_meter = "mystery+tension",
                trigger_value = max(v.mystery, v.tension),
                description   = description
            )

        # Emotional Moment: high connection + high tension
        if v.connection > 70 and v.tension > 60:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.EMOTIONAL_MOMENT,
                trigger_meter = "connection+tension",
                trigger_value = v.connection,
                description   = (
                    "The high emotional connection with characters combined with the current tension "
                    "demands a moment of emotional impact: an impossible moral decision, a betrayal, or a sacrifice."
                )
            )

        # ── Priority 2: Individual Thresholds ─────────────────────────────────

        # Arc Closure (precedence over Plot Twist)
        if v.saturation > 95:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.ARC_CLOSURE,
                trigger_meter = "saturation",
                trigger_value = v.saturation,
                description   = (
                    "The current narrative arc is completely exhausted. It MUST be resolved or closed now. "
                    "The story enters a new chapter or reaches its final conclusion."
                )
            )

        # Climax (extreme tension)
        if v.tension > 85:
            if high_tension_turns <= 2:
                description = (
                    f"Tension has reached its absolute peak (Turn {high_tension_turns} of Extreme Tension). "
                    f"A direct confrontation with the central conflict MUST occur. It cannot be postponed."
                )
            else:
                description = (
                    f"Tension has been extremely high for {high_tension_turns} chapters. The confrontation is "
                    f"entering its final phase. You MUST begin the resolution or release of tension in the narrative. "
                    f"You are required to return a significantly negative 'tension' delta (between -20 and -45) "
                    f"to cool down the scene."
                )

            return ForcedEventConstraint(
                event_type    = ForcedEventType.CLIMAX,
                trigger_meter = "tension",
                trigger_value = v.tension,
                description   = description
            )

        # Tragedy (hope at its limit)
        if v.hope < 10:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.TRAGEDY,
                trigger_meter = "hope",
                trigger_value = v.hope,
                description   = (
                    "Hope has collapsed. An irreversible event of loss MUST occur, confirming "
                    "that the situation is as dire as it seems."
                )
            )

        # Chaos Storm
        if v.chaos > 80:
            if high_chaos_turns <= 2:
                description = (
                    f"The world is in absolute chaos (Turn {high_chaos_turns} of Extreme Chaos). "
                    f"An unpredictable external event MUST disrupt the environment, outside the control of the protagonist."
                )
            else:
                description = (
                    f"Chaos has persisted for {high_chaos_turns} chapters. The situation must begin to settle down. "
                    f"You MUST narrate how the scene stabilizes after the storm and return a significantly negative "
                    f"'chaos' delta (between -20 and -40) to settle the world state."
                )

            return ForcedEventConstraint(
                event_type    = ForcedEventType.CHAOS_STORM,
                trigger_meter = "chaos",
                trigger_value = v.chaos,
                description   = description
            )

        # Plot Twist (high saturation)
        if v.saturation > 85:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.PLOT_TWIST,
                trigger_meter = "saturation",
                trigger_value = v.saturation,
                description   = (
                    "The story needs a twist. Something new MUST be introduced: "
                    "an unexpected character, a sudden revelation, or a change of scenery that renews the conflict."
                )
            )

        # Too Quiet Story (very low tension)
        if v.tension < 15:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.DISRUPTIVE,
                trigger_meter = "tension",
                trigger_value = v.tension,
                description   = (
                    "The story is too quiet. A new threat or conflict MUST be introduced to reactivate the drama."
                )
            )

        # Unexpected Threat (too much optimism)
        if v.hope > 90:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.UNEXPECTED_THREAT,
                trigger_meter = "hope",
                trigger_value = v.hope,
                description   = (
                    "Everything is going too well. An unexpected problem MUST emerge to "
                    "prevent a too comfortable or safe ending."
                )
            )

        # Narrative Rest (sustained high rhythm)
        if v.rhythm > 90 and v._high_rhythm_turns >= 3:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.NARRATIVE_REST,
                trigger_meter = "rhythm",
                trigger_value = v.rhythm,
                description   = (
                    "The pace has been intense for several turns. There MUST be a scene of pause: "
                    "introspection, meaningful dialogue, or a moment of calm before the next storm."
                )
            )

        # No thresholds crossed: the story advances freely
        return None

    def get_dramatic_summary(self) -> str:
        """
        Summary of the dramatic state to include in the AI context.
        The AI uses this to understand the current 'emotional climate'.
        """
        v = self.vector
        lines = [
            "CURRENT DRAMATIC STATE:",
            f"  Tension:     {v.tension}/100  {'🔴' if v.tension > 70 else '🟡' if v.tension > 40 else '🟢'}",
            f"  Hope:        {v.hope}/100  {'🟢' if v.hope > 60 else '🟡' if v.hope > 30 else '🔴'}",
            f"  Chaos:       {v.chaos}/100",
            f"  Rhythm:      {v.rhythm}/100",
            f"  Saturation:  {v.saturation}/100",
            f"  Connection:  {v.connection}/100",
            f"  Mystery:     {v.mystery}/100",
        ]
        return "\n".join(lines)

    def get_arc_analysis(self) -> dict:
        """
        Analysis of the dramatic arc for the paper.
        Calculates metrics on the tension curve throughout the story.
        """
        if len(self._history) < 2:
            return {"error": "Story too short for analysis"}

        tension_curve = [h["tension"] for h in self._history]
        hope_curve    = [h["hope"] for h in self._history]

        return {
            "total_events":      len(self._history),
            "tension_max":       max(tension_curve),
            "tension_min":       min(tension_curve),
            "tension_avg":       sum(tension_curve) / len(tension_curve),
            "tension_variance":  self._variance(tension_curve),
            "hope_avg":          sum(hope_curve) / len(hope_curve),
            "dramatic_peaks":    sum(1 for t in tension_curve if t > 75),
            "low_points":        sum(1 for t in tension_curve if t < 25),
        }

    @staticmethod
    def _variance(values: list[int]) -> float:
        n    = len(values)
        mean = sum(values) / n
        return sum((x - mean) ** 2 for x in values) / n
