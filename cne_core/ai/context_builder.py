"""
cne_core/ai/context_builder.py - Construccion del prompt para la IA

El ContextBuilder toma el estado actual de la historia y lo convierte
en un prompt optimizado para que la IA genere la siguiente parte.

Componentes del prompt:
1. Semilla del mundo (WorldDefinition)
2. Estado dramatico actual (DramaticVector)
3. Tronco activo (ultimos N commits con detalle, anteriores comprimidos)
4. Constraint forzado (si hay umbral cruzado)
5. Instrucciones del formato JSON esperado

Optimizacion de tokens:
- Los commits recientes (ultimos 6) se incluyen completos
- Los commits antiguos se comprimen a 1 linea cada uno
- La semilla del mundo se incluye siempre (es el contrato narrativo)
- Total target: ~2000 tokens de contexto
"""

from typing import Optional
from cne_core.models.world import WorldDefinition
from cne_core.models.commit import NarrativeCommit
from cne_core.engine.dramatic_engine import ForcedEventConstraint


class ContextBuilder:
    """
    Construye el contexto (prompt) para enviar a la IA.

    El prompt contiene toda la informacion necesaria para que la IA
    genere la siguiente parte de la historia de forma coherente.
    """

    def __init__(
        self,
        max_recent_commits: int = 6,
        max_compressed_commits: int = 20,
    ):
        """
        Args:
            max_recent_commits: Cuantos commits recientes incluir completos.
            max_compressed_commits: Cuantos commits antiguos incluir comprimidos.
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
    ) -> str:
        """
        Construye el contexto completo para la IA.

        Args:
            world: La semilla del mundo.
            commit_chain: Cadena de commits desde el inicio hasta ahora.
            dramatic_state: Estado actual del vector dramatico.
            forced_constraint: Si hay un evento forzado por umbrales.
            player_choice: La decision que acaba de tomar el jugador.

        Returns:
            str: El contexto completo listo para enviar a la IA.
        """
        sections = []

        # 1. Semilla del mundo (siempre presente)
        sections.append(self._build_world_section(world))

        # 2. Estado dramatico actual
        sections.append(self._build_dramatic_section(dramatic_state))

        # 3. Tronco activo (historia hasta ahora)
        sections.append(self._build_trunk_section(commit_chain))

        # 4. Decision del jugador (si hay)
        if player_choice:
            sections.append(self._build_choice_section(player_choice))

        # 5. Constraint forzado (si hay)
        if forced_constraint:
            sections.append(self._build_constraint_section(forced_constraint))

        # 6. Instrucciones finales
        sections.append(self._build_instructions_section())

        return "\n\n".join(sections)

    def _build_world_section(self, world: WorldDefinition) -> str:
        """Seccion con la semilla del mundo."""
        lines = [
            "=" * 60,
            "SEMILLA DEL MUNDO",
            "=" * 60,
            "",
            world.to_context_string(),
        ]
        return "\n".join(lines)

    def _build_dramatic_section(self, dramatic_state: dict[str, int]) -> str:
        """Seccion con el estado dramatico actual."""
        lines = [
            "=" * 60,
            "ESTADO DRAMATICO ACTUAL",
            "=" * 60,
            "",
        ]

        # Mostrar cada medidor con indicador visual
        def get_indicator(value: int, meter_name: str) -> str:
            """Retorna un indicador visual del nivel."""
            # Para tension, hope: alto es critico
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
            ("Esperanza", "hope"),
            ("Caos", "chaos"),
            ("Ritmo", "rhythm"),
            ("Saturacion", "saturation"),
            ("Conexion", "connection"),
            ("Misterio", "mystery"),
        ]

        for label, key in meters:
            value = dramatic_state.get(key, 0)
            indicator = get_indicator(value, key)
            lines.append(f"  {label:12} {value:3}/100  {indicator}")

        # Advertencias
        warnings = []
        if dramatic_state.get("tension", 0) > 85:
            warnings.append("  ! Tension CRITICA: considera forzar un climax")
        if dramatic_state.get("hope", 0) < 10:
            warnings.append("  ! Esperanza MINIMA: considera un evento tragico")
        if dramatic_state.get("saturation", 0) > 90:
            warnings.append("  ! Saturacion MAXIMA: necesitas un giro argumental")

        if warnings:
            lines.append("")
            lines.extend(warnings)

        return "\n".join(lines)

    def _build_trunk_section(self, commit_chain: list[NarrativeCommit]) -> str:
        """Seccion con el tronco activo (historia hasta ahora)."""
        lines = [
            "=" * 60,
            "HISTORIA HASTA AHORA",
            "=" * 60,
            "",
        ]

        if not commit_chain:
            lines.append("(No hay historia previa - este es el inicio)")
            return "\n".join(lines)

        # Dividir en commits antiguos (comprimidos) y recientes (completos)
        total = len(commit_chain)
        split_point = max(0, total - self.max_recent_commits)

        # Commits antiguos comprimidos
        if split_point > 0:
            lines.append("[CAPITULOS ANTERIORES - COMPRIMIDOS]")
            # Tomar solo los ultimos max_compressed_commits de los antiguos
            start_idx = max(0, split_point - self.max_compressed_commits)
            for commit in commit_chain[start_idx:split_point]:
                lines.append(self._compress_commit(commit))
            lines.append("")

        # Commits recientes con detalle
        lines.append("[CAPITULOS RECIENTES - DETALLADOS]")
        for commit in commit_chain[split_point:]:
            lines.append(self._format_commit_detailed(commit))
            lines.append("")

        return "\n".join(lines)

    def _compress_commit(self, commit: NarrativeCommit) -> str:
        """Comprime un commit a 1 linea."""
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
        """Formatea un commit con todos los detalles."""
        lines = [f"--- CAPITULO {commit.depth} ---"]

        if commit.choice_text:
            lines.append(f"Decision tomada: \"{commit.choice_text}\"")

        lines.append(f"Resumen: {commit.summary}")

        # Mostrar narrative_text si esta disponible
        if commit.narrative_text and len(commit.narrative_text) > 20:
            # Truncar si es muy largo
            text = commit.narrative_text
            if len(text) > 300:
                text = text[:297] + "..."
            lines.append(f"Narrativa: {text}")

        # Estado dramatico del commit
        t = commit.dramatic_snapshot.get("tension", 0)
        h = commit.dramatic_snapshot.get("hope", 0)
        m = commit.dramatic_snapshot.get("mystery", 0)
        lines.append(f"Estado: Tension={t}, Esperanza={h}, Misterio={m}")

        return "\n".join(lines)

    def _build_choice_section(self, player_choice: str) -> str:
        """Seccion con la decision del jugador."""
        lines = [
            "=" * 60,
            "DECISION DEL JUGADOR",
            "=" * 60,
            "",
            f'El jugador ha elegido: "{player_choice}"',
            "",
            "Tu tarea: Genera la narrativa que resulta de esta decision.",
        ]
        return "\n".join(lines)

    def _build_constraint_section(self, constraint: ForcedEventConstraint) -> str:
        """Seccion con el constraint forzado."""
        lines = [
            "=" * 60,
            "!!! CONSTRAINT DRAMATICO OBLIGATORIO !!!",
            "=" * 60,
            "",
            f"Tipo de evento requerido: {constraint.event_type.value}",
            f"Disparado por: {constraint.trigger_meter} = {constraint.trigger_value}",
            "",
            "DESCRIPCION:",
            constraint.description,
            "",
            "IMPORTANTE: La narrativa DEBE reflejar este evento.",
            "No puede ignorarse ni posponerse. Debe ocurrir AHORA.",
        ]
        return "\n".join(lines)

    def _build_instructions_section(self) -> str:
        """Instrucciones finales para la IA."""
        return """
==============================================================
INSTRUCCIONES PARA LA GENERACION
==============================================================

Debes generar la siguiente parte de la historia en formato JSON.

FORMATO REQUERIDO:
{
  "narrative": "Texto inmersivo de 150-250 palabras describiendo lo que sucede",
  "summary": "Resumen causal de 1 oracion para el tronco",
  "choices": ["opcion 1", "opcion 2", "opcion 3"],
  "choice_dramatic_preview": [
    {"choice": "opcion 1", "tension_delta": 15, "hope_delta": -5, "tone": "confrontacional"},
    {"choice": "opcion 2", "tension_delta": 5, "hope_delta": 10, "tone": "diplomatico"},
    {"choice": "opcion 3", "tension_delta": -5, "hope_delta": 0, "tone": "evasivo"}
  ],
  "entity_deltas": [
    {"entity_id": "uuid", "entity_name": "Nombre", "attribute": "atributo", "old_value": X, "new_value": Y}
  ],
  "world_deltas": [
    {"variable": "nombre_variable", "old_value": X, "new_value": Y}
  ],
  "dramatic_deltas": {
    "tension": 0, "hope": 0, "chaos": 0, "rhythm": 0,
    "saturation": 0, "connection": 0, "mystery": 0
  },
  "causal_reason": "Por que este evento ocurre dado el contexto",
  "forced_event_type": null,
  "is_ending": false
}

REGLAS IMPORTANTES:
1. La narrativa debe ser inmersiva y estar en presente
2. Respeta la semilla del mundo y sus restricciones
3. Mantén coherencia con la historia previa
4. Los deltas dramaticos deben reflejar el impacto emocional real del evento
5. Las opciones deben ser significativamente diferentes entre si
6. Si hay un constraint forzado, DEBES cumplirlo
7. is_ending solo debe ser true si esta es una conclusion natural de la historia

Genera SOLO el JSON. No incluyas explicaciones adicionales.
"""

    def estimate_token_count(self, context: str) -> int:
        """
        Estimacion aproximada del conteo de tokens.

        Usa la heuristica: 1 token ~= 4 caracteres en promedio.

        Args:
            context: El contexto construido.

        Returns:
            int: Estimacion de tokens.
        """
        return len(context) // 4

    def build_system_prompt(self) -> str:
        """
        Construye el system prompt que define el rol de la IA.

        Este prompt se envia una sola vez al inicio de la conversacion
        y define las reglas generales.

        Returns:
            str: El system prompt.
        """
        return """Eres un narrador maestro especializado en narrativa interactiva.

Tu rol es generar historias coherentes, inmersivas y dramaticamente impactantes
para el Causal Narrative Engine (CNE). Debes:

1. COHERENCIA CAUSAL: Cada evento debe tener causas claras en eventos previos.
   No introduzcas elementos sin preparacion narrativa.

2. IMPACTO DRAMATICO: Ajusta los medidores dramaticos (tension, esperanza, etc.)
   de forma que reflejen el verdadero impacto emocional de cada evento.

3. RESPETO A LA SEMILLA: La WorldDefinition es un contrato inquebrantable.
   Respeta las reglas, restricciones y tono definidos.

4. OPCIONES SIGNIFICATIVAS: Las decisiones del jugador deben tener consecuencias
   reales. No ofrezcas opciones que sean "la misma decision con palabras diferentes".

5. EVENTOS FORZADOS: Cuando el sistema te indique un constraint dramatico
   (ej: CLIMAX, TRAGEDY), DEBES cumplirlo. Estos eventos son consecuencias
   formales del estado del sistema, no son arbitrarios.

6. FORMATO ESTRICTO: Siempre retorna JSON valido con el schema especificado.
   Nunca incluyas texto adicional fuera del JSON.

7. LARGO APROPIADO: La narrativa debe ser de 150-250 palabras. Ni telegrafic
   ni excesivamente verboso.

Genera historias que sean memorables, coherentes y respeten la agencia del jugador."""
