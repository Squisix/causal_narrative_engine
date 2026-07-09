"""
cne_core/ai/context_builder.py - AI Prompt Context Builder

Constructs optimized prompts for the AI to generate the next narrative segment.

Prompt Structure:
1. World seed (WorldDefinition)
2. Current entity states (characters, factions, artifacts)
3. Global world variables
4. Current dramatic state (7 meters)
5. Active history trunk (comprising recent detailed chapters and compressed older chapters)
6. Player choice (if applicable)
7. Forced constraint (if any threshold is crossed)
8. Output JSON structure instructions and language guidelines

Token optimization:
- Recent commits (last 6) are included with full detail.
- Older commits are compressed into a single line each.
- The world seed is always included to maintain the narrative contract.
- Target context: ~2000 tokens.
"""

from typing import Optional
from cne_core.models.world import WorldDefinition
from cne_core.models.commit import NarrativeCommit
from cne_core.engine.dramatic_engine import ForcedEventConstraint


class ContextBuilder:
    """
    Builds the context (prompt) to send to the AI.

    Contains all necessary information to ensure narrative coherence,
    causal logic, and dramatic tension.
    """

    def __init__(
        self,
        max_recent_commits: int = 6,
        max_compressed_commits: int = 20,
    ):
        """
        Args:
            max_recent_commits: Number of recent commits to include with full details.
            max_compressed_commits: Number of older commits to include as compressed single lines.
        """
        self.max_recent_commits = max_recent_commits
        self.max_compressed_commits = max_compressed_commits

    def build_context(
        self,
        world: WorldDefinition,
        commit_chain: list[NarrativeCommit],
        dramatic_state: dict[str, int],
        forced_constraint: Optional[ForcedEventConstraint] = None,
        player_choice: Optional[str] = None,
        player_choice_tone: Optional[str] = None,
        current_entity_states: Optional[dict] = None,
        current_world_vars: Optional[dict] = None,
    ) -> str:
        """
        Builds the entire prompt context for the AI.

        Args:
            world: The world seed.
            commit_chain: Chain of commits from the beginning of the story.
            dramatic_state: Current dramatic vector meters.
            forced_constraint: Forced event constraints from crossed thresholds.
            player_choice: The choice made by the player.
            current_entity_states: Current attributes of world entities.
            current_world_vars: Global variables of the world state.

        Returns:
            str: Complete system prompt context.
        """
        sections = []

        # 1. World seed (always present)
        sections.append(self._build_world_section(world))

        # 2. Current entity states
        if current_entity_states:
            sections.append(self._build_entity_states_section(current_entity_states))

        # 3. Global world variables
        if current_world_vars:
            sections.append(self._build_world_vars_section(current_world_vars))

        # 4. Current dramatic state
        sections.append(self._build_dramatic_section(dramatic_state))

        # 5. History trunk (story so far)
        sections.append(self._build_trunk_section(commit_chain))

        # 6. Player choice
        if player_choice:
            sections.append(self._build_choice_section(player_choice, player_choice_tone))

        # 7. Forced constraint
        if forced_constraint:
            sections.append(self._build_constraint_section(forced_constraint))

        # 8. Generation instructions & JSON schema
        sections.append(self._build_instructions_section(world))

        return "\n\n".join(sections)

    def _build_world_section(self, world: WorldDefinition) -> str:
        """Section with the immutable world seed."""
        lines = [
            "=" * 60,
            "WORLD SEED",
            "=" * 60,
            "",
            world.to_context_string(),
        ]
        return "\n".join(lines)

    def _build_entity_states_section(self, entity_states: dict) -> str:
        """Section with the current attributes of all entities."""
        characters = []
        artifacts = []
        others = []

        for eid, state in entity_states.items():
            etype = state.get("type", "unknown")
            if etype == "artifact":
                artifacts.append((eid, state))
            elif etype == "character":
                characters.append((eid, state))
            else:
                others.append((eid, state))

        lines = [
            "=" * 60,
            "CURRENT ENTITY STATES",
            "=" * 60,
        ]

        if characters or others:
            lines.append("")
            lines.append("[CHARACTERS & FACTIONS]")
            for eid, state in characters + others:
                lines.extend(self._format_entity_line(eid, state))

        if artifacts:
            lines.append("")
            lines.append("[ITEMS & ARTIFACTS]")
            for eid, state in artifacts:
                attrs = state.get("attributes", {})
                possessed_by = attrs.get("possessed_by")
                location = attrs.get("location", "unknown")
                possession_str = f" | Possessed by: {possessed_by}" if possessed_by else f" | Available at: {location}"
                lines.extend(self._format_entity_line(eid, state, extra=possession_str))

        return "\n".join(lines)

    def _format_entity_line(self, eid: str, state: dict, extra: str = "") -> list[str]:
        name = state.get("name", eid)
        etype = state.get("type", "unknown")
        alive = state.get("alive", True)
        attrs = state.get("attributes", {})
        display_attrs = {k: v for k, v in attrs.items() if k not in ("created_at_depth",)}
        status = "" if alive else " [DEAD/DESTROYED]"
        attrs_str = ", ".join(f"{k}={v}" for k, v in display_attrs.items())
        return [
            f"  {name} ({etype}){status}: {attrs_str}{extra}",
            f"    [entity_id: {eid}]",
        ]

    def _build_world_vars_section(self, world_vars: dict) -> str:
        """Section with global world variables."""
        lines = [
            "=" * 60,
            "GLOBAL WORLD VARIABLES",
            "=" * 60,
            "",
        ]

        for var_name, value in world_vars.items():
            lines.append(f"  {var_name}: {value}")

        return "\n".join(lines)

    def _build_dramatic_section(self, dramatic_state: dict[str, int]) -> str:
        """Section with the current dramatic meters."""
        lines = [
            "=" * 60,
            "CURRENT DRAMATIC STATE",
            "=" * 60,
            "",
        ]

        def get_indicator(value: int, meter_name: str) -> str:
            """Returns a visual severity indicator for the meter value."""
            if meter_name in ["tension", "chaos", "saturation"]:
                if value > 80:
                    return "[!!!]"
                elif value > 60:
                    return "[!!]"
                elif value > 40:
                    return "[!]"
                else:
                    return "[ ]"
            elif meter_name == "hope":
                if value < 20:
                    return "[!!!]"
                elif value < 40:
                    return "[!!]"
                elif value < 60:
                    return "[!]"
                else:
                    return "[ ]"
            else:
                return ""

        meters = [
            ("Tension", "tension"),
            ("Hope", "hope"),
            ("Chaos", "chaos"),
            ("Rhythm", "rhythm"),
            ("Saturation", "saturation"),
            ("Connection", "connection"),
            ("Mystery", "mystery"),
        ]

        for label, key in meters:
            value = dramatic_state.get(key, 0)
            indicator = get_indicator(value, key)
            lines.append(f"  {label:12} {value:3}/100  {indicator}")

        # Dramatic threshold warnings
        warnings = []
        if dramatic_state.get("tension", 0) > 85:
            warnings.append("  ! CRITICAL Tension: consider forcing a Climax")
        if dramatic_state.get("hope", 0) < 10:
            warnings.append("  ! MINIMUM Hope: consider forcing a Tragedy")
        if dramatic_state.get("saturation", 0) > 90:
            warnings.append("  ! MAXIMUM Saturation: a Plot Twist is required")

        if warnings:
            lines.append("")
            lines.extend(warnings)

        return "\n".join(lines)

    def _build_trunk_section(self, commit_chain: list[NarrativeCommit]) -> str:
        """Section with the history trunk."""
        lines = [
            "=" * 60,
            "STORY SO FAR",
            "=" * 60,
            "",
        ]

        if not commit_chain:
            lines.append("(No previous history - this is the beginning of the story)")
            return "\n".join(lines)

        total = len(commit_chain)
        split_point = max(0, total - self.max_recent_commits)

        # Older compressed commits
        if split_point > 0:
            lines.append("[OLDER CHAPTERS - COMPRESSED]")
            start_idx = max(0, split_point - self.max_compressed_commits)
            for commit in commit_chain[start_idx:split_point]:
                lines.append(self._compress_commit(commit))
            lines.append("")

        # Recent detailed commits
        lines.append("[RECENT CHAPTERS - DETAILED]")
        for commit in commit_chain[split_point:]:
            lines.append(self._format_commit_detailed(commit))
            lines.append("")

        return "\n".join(lines)

    def _compress_commit(self, commit: NarrativeCommit) -> str:
        """Compresses a commit to a single line."""
        choice_prefix = ""
        if commit.choice_text:
            choice_prefix = f'[{commit.choice_text[:30]}...] '

        t = commit.dramatic_snapshot.get("tension", 0)
        h = commit.dramatic_snapshot.get("hope", 0)

        return (
            f"  Cap.{commit.depth}: {choice_prefix}{commit.summary} "
            f"(T={t}, H={h})"
        )

    def _format_commit_detailed(self, commit: NarrativeCommit) -> str:
        """Formats a commit with full narrative details."""
        lines = [f"--- CHAPTER {commit.depth} ---"]

        if commit.choice_text:
            lines.append(f"Choice taken: \"{commit.choice_text}\"")

        lines.append(f"Summary: {commit.summary}")

        if commit.narrative_text and len(commit.narrative_text) > 20:
            text = commit.narrative_text
            if len(text) > 300:
                text = text[:297] + "..."
            lines.append(f"Narrative: {text}")

        t = commit.dramatic_snapshot.get("tension", 0)
        h = commit.dramatic_snapshot.get("hope", 0)
        m = commit.dramatic_snapshot.get("mystery", 0)
        lines.append(f"State: Tension={t}, Hope={h}, Mystery={m}")

        return "\n".join(lines)

    def _build_choice_section(self, player_choice: str, player_choice_tone: Optional[str] = None) -> str:
        """Section with the player's taken choice."""
        tone_str = f" (tone: {player_choice_tone})" if player_choice_tone else ""
        lines = [
            "=" * 60,
            "PLAYER CHOICE",
            "=" * 60,
            "",
            f'The player selected: "{player_choice}"{tone_str}',
            "",
            "Your task: Write the narrative resulting from this decision.",
            "Honor the emotional tone the player chose for their action.",
        ]
        return "\n".join(lines)

    def _build_constraint_section(self, constraint: ForcedEventConstraint) -> str:
        """Section with the forced dramatic constraint."""
        lines = [
            "=" * 60,
            "!!! MANDATORY DRAMATIC CONSTRAINT !!!",
            "=" * 60,
            "",
            f"Event type required: {constraint.event_type.value}",
            f"Triggered by: {constraint.trigger_meter} = {constraint.trigger_value}",
            "",
            "DESCRIPTION:",
            constraint.description,
            "",
            "IMPORTANT: The generated narrative MUST reflect this constraint.",
            "It cannot be postponed or bypassed. It must happen NOW.",
        ]
        return "\n".join(lines)

    def _build_instructions_section(self, world: WorldDefinition) -> str:
        """Final generation instructions for the AI, injecting output language."""
        return f"""
==============================================================
GENERATION INSTRUCTIONS
==============================================================

You must generate the next part of the story in the requested JSON format.

CRITICAL INSTRUCTION ON LANGUAGE:
- You MUST write the narrative values ("narrative", "summary", and the choices array text) in "{world.output_language}" language.
- All JSON schema keys, entity types, tones, and status identifiers MUST remain in English as defined below.

REQUIRED SCHEMA FORMAT:
{{
  "narrative": "Immersive narrative text of 150-250 words describing what happens, written in {world.output_language}",
  "summary": "1-sentence causal summary for the history trunk, written in {world.output_language}",
  "choices": ["choice 1 in {world.output_language}", "choice 2 in {world.output_language}", "choice 3 in {world.output_language}"],
  "choice_tones": ["confrontational", "diplomatic", "evasive"],
  "entity_deltas": [
    {{"entity_id": "uuid", "entity_name": "Name", "attribute": "attribute", "old_value": X, "new_value": Y}}
  ],
  "entity_creations": [
    {{"entity_name": "Name", "entity_type": "character|faction|artifact|location", "attributes": {{"key": "value"}}}}
  ],
  "world_deltas": [
    {{"variable": "variable_name", "old_value": X, "new_value": Y}}
  ],
  "dramatic_deltas": {{
    "tension": 0, "hope": 0, "chaos": 0, "rhythm": 0,
    "saturation": 0, "connection": 0, "mystery": 0
  }},
  "causal_reason": "Why this event occurs given the context",
  "forced_event_type": null,
  "is_ending": false
}}

IMPORTANT RULES:
1. The narrative must be immersive, active, and written in the present tense.
2. Respect the world seed and its constraints.
3. Maintain consistency with the previous story.
4. Dramatic deltas must reflect the real emotional impact of the event.
5. Choices must be significantly different from one another.
6. If there is a forced constraint, you MUST satisfy it.
7. is_ending should only be true if this is a natural conclusion of the story.

ENTITY CREATION (entity_creations):
- Introduce new characters, factions, artifacts, or locations when the narrative requires it.
- Use entity_creations to formally register them in the world state.
- entity_type must be: "character", "faction", "artifact", or "location".

ITEMS AND ARTEFACTS:
- When a significant object appears (key, book, weapon, potion, relic, map, etc.), create it as an "artifact" entity in entity_creations.
- Required attributes for artifacts:
  - "possessed_by": null if available in the environment, or the name of the character holding it.
  - "location": where the item is currently situated.
  - "usable": true/false if it can be used right now.
  - "effect": a brief description of its effect or meaning.
- When a character PICKS UP an item, generate an entity_delta changing "possessed_by": null -> "possessed_by": "character's name".
- If items are available in the scene (possessed_by=null), generate at least one choice involving interaction with them (e.g., "Pick up the rusty key", "Read the grimoire").

Generate ONLY the JSON response. Do not include any preambles, explanations, or markdown fences except the raw JSON.
"""

    def estimate_token_count(self, context: str) -> int:
        """
        Rough estimate of token count based on string length.

        Uses the heuristic: 1 token ~= 4 characters on average.

        Args:
            context: The constructed context.

        Returns:
            int: Estimated token count.
        """
        return len(context) // 4

    def build_system_prompt(self) -> str:
        """
        Builds the system prompt that defines the AI's role.

        This prompt is sent once at the beginning of the conversation
        and defines the core operational mandates.

        Returns:
            str: The system prompt.
        """
        return """You are a master storyteller specialized in interactive narrative.

Your role is to generate coherent, immersive, and dramatically impactful stories for the Causal Narrative Engine (CNE). You must:

1. CAUSAL COHERENCE: Every event must have clear causes in previous events. Do not introduce elements without proper narrative preparation.

2. DRAMATIC IMPACT: Adjust the dramatic meters (tension, hope, etc.) so that they reflect the true emotional impact of each event.

3. RESPECT FOR THE SEED: The WorldDefinition is an unbreakable contract. Respect the defined rules, constraints, and tone.

4. SIGNIFICANT CHOICES: The player's decisions must have real consequences. Do not offer choices that are "the same decision with different words."

5. FORCED EVENTS: When the system indicates a dramatic constraint (e.g., CLIMAX, TRAGEDY), you MUST comply. These events are formal consequences of the system state, not arbitrary interruptions.

6. STRICT FORMATTING: Always return valid JSON matching the specified schema. Never include any additional text outside of the JSON.

7. APPROPRIATE LENGTH: The narrative must be between 150-250 words. Neither telegraphic nor excessively verbose.

8. DYNAMIC ENTITIES: Introduce new characters, factions, locations, and significant objects (keys, weapons, books, relics) using entity_creations. Significant objects must be created as "artifact" type with possession attributes. When items are available in the scene, offer choices to interact with them.

Generate stories that are memorable, coherent, and respect the player's agency."""
