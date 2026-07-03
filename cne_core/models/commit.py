"""
models/commit.py — Git-like versioning of the narrative tree

A NarrativeCommit is like a Git commit:
- It has a parent (the previous commit)
- It records what decision was made
- It saves the state of the world at that moment
- It can branch (a commit can have multiple children)

This is what makes it possible to:
- Go back in the story
- Explore alternative branches
- Compare what would have happened with a different decision
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


# ── NarrativeCommit ───────────────────────────────────────────────────────────

@dataclass
class NarrativeCommit:
    """
    A point in the story. Equivalent to a Git commit.

    The story is not saved as linear text, but as a chain
    of commits. Each commit points to its parent (parent_id), forming
    a tree that can branch.

    Tree example:
        commit_0 (start)
            └─ commit_1 (decision: "talk to the king")
                ├─ commit_2a (decision: "accept the mission")  ← branch A
                └─ commit_2b (decision: "reject the mission") ← branch B

    Attributes:
        world_id:        Which WorldDefinition this belongs to.
        parent_id:       The previous commit. None only for the first one.
        event_id:        The NarrativeEvent that generated this commit.
        choice_text:     The decision as text (what the player chose).
        narrative_text:  The full narrative text for this moment.
        summary:         1-sentence summary (for trunk compression).
        depth:           How many decisions have been made up to here.
        branch_id:       Identifier of the branch we are on.
        dramatic_snapshot: State of the DramaticVector at this commit.
        world_state_snapshot: State of the global world variables.
        entity_states:   State of entities at this commit.
        is_ending:       Is this the end of the story?
        children_ids:    IDs of child commits (alternative branches).
    """
    world_id:      str
    event_id:      str
    depth:         int

    parent_id:     str | None     = None   # None only for the root commit
    choice_text:   str | None     = None   # None for the initial commit
    narrative_text: str           = ""
    summary:       str            = ""

    branch_id:     str            = field(default_factory=lambda: str(uuid.uuid4()))

    # World state at this commit (lightweight snapshot)
    dramatic_snapshot:    dict[str, int]  = field(default_factory=dict)
    world_state_snapshot: dict[str, Any]  = field(default_factory=dict)
    entity_states:        dict[str, Any]  = field(default_factory=dict)

    is_ending:     bool           = False
    children_ids:  list[str]      = field(default_factory=list)

    id:            str            = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:    datetime       = field(default_factory=datetime.now)

    @property
    def is_root(self) -> bool:
        """Is this the first commit in the story?"""
        return self.parent_id is None

    @property
    def has_branches(self) -> bool:
        """Does it have multiple paths from here?"""
        return len(self.children_ids) > 1

    def add_child(self, child_id: str) -> None:
        """Registers a child commit (when the player makes a decision here)."""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)

    def get_dramatic_meter(self, meter: str) -> int:
        """Safe access to a meter from the dramatic snapshot."""
        return self.dramatic_snapshot.get(meter, 0)

    def to_trunk_entry(self) -> str:
        """
        Compact representation for the active trunk.
        Distant commits are included in the AI context
        using this single-line representation.
        """
        prefix = ""
        if self.choice_text:
            prefix = f'-> "{self.choice_text}" | '

        tension = self.get_dramatic_meter("tension")
        hope    = self.get_dramatic_meter("hope")

        return (
            f"[Ch.{self.depth}] {prefix}{self.summary} "
            f"(tension={tension}, hope={hope})"
        )

    def __str__(self) -> str:
        choice = f'"{self.choice_text}"' if self.choice_text else "beginning"
        return (
            f"NarrativeCommit("
            f"depth={self.depth}, "
            f"choice={choice}, "
            f"branches={len(self.children_ids)})"
        )


# ── Branch ────────────────────────────────────────────────────────────────────

@dataclass
class Branch:
    """
    Metadata for a branch of the narrative tree.

    A branch is a sequence of commits from a divergence point
    to the current leaf (or an ending). When the player goes back
    and makes a different decision, a new branch is created.

    The branch_id is propagated to all commits on that branch.
    """
    world_id:      str
    origin_commit_id: str    # From which commit it diverged
    name:          str       = "Main branch"
    description:   str       = ""
    leaf_commit_id: str | None = None   # The most recent commit on this branch

    id:            str       = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:    datetime  = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Branch('{self.name}', origin={self.origin_commit_id[:8]}...)"


# ── NarrativeChoice ───────────────────────────────────────────────────────────

@dataclass
class NarrativeChoice:
    """
    An available option for the player at a given moment.

    The leaves of the literary tree. The AI generates them, the engine validates
    them and presents them. The player chooses one -> new commit -> new branch if
    there was already a child commit at this point.

    dramatic_preview shows how we ESTIMATE the dramatic vector will change
    if this option is chosen. It is an AI prediction,
    not an engine guarantee.
    """
    text:             str                    # The option text
    dramatic_preview: dict[str, int]         = field(default_factory=dict)
    tone_hint:        str                    = ""   # "confrontational", "diplomatic", etc.
    estimated_depth_until_ending: int | None = None

    def get_preview_str(self) -> str:
        """Summary of the estimated dramatic impact to show the player."""
        if not self.dramatic_preview:
            return ""
        parts = []
        for meter, delta in self.dramatic_preview.items():
            if delta != 0:
                sign  = "+" if delta > 0 else ""
                arrow = "^" if delta > 0 else "v"
                parts.append(f"{arrow}{meter}{sign}{delta}")
        return "  ".join(parts[:3])   # Show at most 3 to avoid cluttering the UI

    def __str__(self) -> str:
        return f"NarrativeChoice('{self.text[:40]}...')"
