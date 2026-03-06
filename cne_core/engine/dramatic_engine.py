"""
engine/dramatic_engine.py — El Sistema Dramático Multi-Medidor (SDMM)

Este módulo implementa la función Φ del modelo formal:
    Φ(D(t)) → constraint de evento forzado (o None)

El DramaticEngine mantiene el vector dramático de 7 medidores
y evalúa si alguno ha cruzado un umbral que requiera forzar
un tipo de evento específico.

La clave innovadora: cuando el motor fuerza un evento (ej: CLÍMAX
porque la tensión > 85), ese evento NO es una interrupción externa.
Se integra causalmente en el DAG: tiene causas formales en todos
los eventos que elevaron la tensión hasta ese punto.
"""

from dataclasses import dataclass, field
from enum import Enum


# ── Tipos de eventos forzados ─────────────────────────────────────────────────

class ForcedEventType(str, Enum):
    """
    Tipos de eventos que el motor puede forzar cuando un medidor
    cruza su umbral. La IA debe respetar este constraint.
    """
    CLIMAX              = "CLIMAX"              # Tensión > 85
    DISRUPTIVE          = "DISRUPTIVE"          # Tensión < 15
    TRAGEDY             = "TRAGEDY"             # Esperanza < 10
    UNEXPECTED_THREAT   = "UNEXPECTED_THREAT"   # Esperanza > 90
    PLOT_TWIST          = "PLOT_TWIST"          # Saturación > 85
    ARC_CLOSURE         = "ARC_CLOSURE"         # Saturación > 95
    CHAOS_STORM         = "CHAOS_STORM"         # Caos > 80
    NARRATIVE_REST      = "NARRATIVE_REST"      # Ritmo > 90 por 3 turnos
    CLIMAX_REVELATION   = "CLIMAX_REVELATION"   # Misterio > 65 Y Tensión > 65
    EMOTIONAL_MOMENT    = "EMOTIONAL_MOMENT"    # Conexión > 70 Y Tensión > 60


@dataclass
class ForcedEventConstraint:
    """
    El constraint que el motor pasa a la IA cuando se fuerza un evento.

    La IA recibe esto en el system prompt y DEBE generar una narrativa
    que corresponda al tipo de evento forzado.
    """
    event_type:    ForcedEventType
    trigger_meter: str     # Qué medidor lo disparó
    trigger_value: int     # Valor en el que estaba el medidor
    description:   str     # Instrucción clara para la IA

    def to_prompt_constraint(self) -> str:
        """Texto a incluir en el prompt de la IA."""
        return (
            f"⚠️ CONSTRAINT DRAMÁTICO OBLIGATORIO: {self.description}\n"
            f"Tipo de evento requerido: {self.event_type.value}\n"
            f"Disparado por: {self.trigger_meter} = {self.trigger_value}\n"
            f"La narrativa DEBE reflejar este momento dramático. "
            f"No puede ignorarse ni posponerse."
        )


# ── DramaticVector ────────────────────────────────────────────────────────────

@dataclass
class DramaticVector:
    """
    El vector de estado dramático D(t).

    7 medidores que capturan el estado emocional y estructural
    de la historia en un momento dado. Todos en rango [0, 100].

    El motor los actualiza después de cada evento:
    1. Aplica el DramaticDelta del evento
    2. Aplica las interacciones entre medidores
    3. Clampea todos los valores a [0, 100]
    4. Evalúa umbrales → ForcedEventConstraint o None
    """
    tension:    int = 30
    hope:       int = 60
    chaos:      int = 20
    rhythm:     int = 50
    saturation: int = 0
    connection: int = 40
    mystery:    int = 50

    # Contador de turnos con ritmo alto (para el umbral de descanso)
    _high_rhythm_turns: int = field(default=0, repr=False)

    def apply_delta(self, delta: "DramaticDelta") -> None:
        """
        Aplica un delta al vector y luego las interacciones entre medidores.

        El orden importa:
        1. Aplicar el delta del evento
        2. Aplicar interacciones causales entre medidores
        3. Clampear a [0, 100]
        """
        # 1. Aplicar delta directo
        self.tension    = self.tension    + delta.tension
        self.hope       = self.hope       + delta.hope
        self.chaos      = self.chaos      + delta.chaos
        self.rhythm     = self.rhythm     + delta.rhythm
        self.saturation = self.saturation + delta.saturation
        self.connection = self.connection + delta.connection
        self.mystery    = self.mystery    + delta.mystery

        # 2. Aplicar interacciones entre medidores
        self._apply_interactions(delta)

        # 3. Clampear al rango válido
        self._clamp()

        # 4. Actualizar contador de ritmo alto
        if self.rhythm > 70:
            self._high_rhythm_turns += 1
        else:
            self._high_rhythm_turns = 0

    def _apply_interactions(self, delta: "DramaticDelta") -> None:
        """
        Interacciones causales entre medidores.

        Estas son las relaciones que hacen el sistema coherente con
        la teoría dramática. Se aplican DESPUÉS del delta directo.
        """
        # Tensión alta erosiona la esperanza
        # Por cada 10 puntos de tensión > 50, esperanza baja -2
        if self.tension > 50:
            hope_erosion = ((self.tension - 50) // 10) * 2
            self.hope -= hope_erosion

        # Caos alto acelera el ritmo
        if self.chaos > 60:
            rhythm_boost = (self.chaos - 60) // 10
            self.rhythm += rhythm_boost

        # Saturación alta desconecta emocionalmente
        if self.saturation > 70:
            connection_loss = (self.saturation - 70) // 5
            self.connection -= connection_loss

        # Esperanza muy baja aumenta el misterio (¿qué está pasando?)
        if self.hope < 20:
            self.mystery += 3

        # Conexión alta amplifica el impacto de la tensión
        # (no modifica el vector, pero afecta cómo se evalúan los umbrales)
        # → ver evaluate_thresholds()

    def _clamp(self) -> None:
        """Mantiene todos los valores en [0, 100]."""
        self.tension    = max(0, min(100, self.tension))
        self.hope       = max(0, min(100, self.hope))
        self.chaos      = max(0, min(100, self.chaos))
        self.rhythm     = max(0, min(100, self.rhythm))
        self.saturation = max(0, min(100, self.saturation))
        self.connection = max(0, min(100, self.connection))
        self.mystery    = max(0, min(100, self.mystery))

    def to_dict(self) -> dict[str, int]:
        """Serializa para persistencia y contexto IA."""
        return {
            "tension": self.tension, "hope": self.hope,
            "chaos": self.chaos, "rhythm": self.rhythm,
            "saturation": self.saturation, "connection": self.connection,
            "mystery": self.mystery,
        }

    def from_dict(self, d: dict[str, int]) -> None:
        """Restaura el vector desde un dict (al cargar un commit)."""
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

# Necesitamos importar DramaticDelta aquí pero está en models/event.py
# Usamos TYPE_CHECKING para evitar importación circular en runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from cne_core.models.event import DramaticDelta


class DramaticEngine:
    """
    La función Φ del modelo formal: evalúa el vector dramático
    y determina si se debe forzar un evento.

    Uso típico:
        engine = DramaticEngine(world_def.dramatic_config)

        # Después de cada decisión del jugador:
        engine.apply_delta(event.dramatic_delta)
        constraint = engine.evaluate_thresholds()

        if constraint:
            # Pasar constraint a la IA como instrucción obligatoria
            prompt = build_prompt(..., forced_constraint=constraint)
        else:
            prompt = build_prompt(...)
    """

    def __init__(self, initial_config: dict[str, int] | None = None):
        """
        Args:
            initial_config: Valores iniciales del vector desde WorldDefinition.
                           Si es None, usa los defaults del DramaticVector.
        """
        self.vector = DramaticVector()

        if initial_config:
            self.vector.from_dict(initial_config)

        # Historial de medidores para análisis (paper)
        self._history: list[dict[str, int]] = [self.vector.to_dict()]

    @property
    def current_state(self) -> dict[str, int]:
        return self.vector.to_dict()

    def apply_delta_from_dict(self, delta_dict: dict[str, int]) -> None:
        """
        Aplica un delta recibido como dict (desde la respuesta de la IA).
        Crea un DramaticDelta y lo aplica al vector.
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
        """Aplica un DramaticDelta al vector y guarda en historial."""
        self.vector.apply_delta(delta)
        self._history.append(self.vector.to_dict())

    def evaluate_thresholds(self) -> ForcedEventConstraint | None:
        """
        Φ: evalúa si algún medidor ha cruzado un umbral.

        Los umbrales se evalúan en orden de prioridad. Si hay múltiples
        umbrales cruzados, solo se reporta el de mayor prioridad.

        Returns:
            ForcedEventConstraint si hay un umbral cruzado,
            None si la historia puede continuar libremente.
        """
        v = self.vector

        # ── Prioridad 1: Combinaciones de dos medidores ────────────────────
        # Estas condiciones tienen mayor precedencia porque son más específicas

        # Clímax de revelación: misterio alto + tensión alta
        if v.mystery > 65 and v.tension > 65:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.CLIMAX_REVELATION,
                trigger_meter = "mystery+tension",
                trigger_value = max(v.mystery, v.tension),
                description   = (
                    "El misterio central DEBE revelarse ahora, en el momento "
                    "de máxima tensión. Una verdad oculta sale a la luz."
                )
            )

        # Momento emocional: conexión alta + tensión alta
        if v.connection > 70 and v.tension > 60:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.EMOTIONAL_MOMENT,
                trigger_meter = "connection+tension",
                trigger_value = v.connection,
                description   = (
                    "La alta conexión emocional con los personajes combinada "
                    "con la tensión actual exige un momento de impacto emocional: "
                    "una decisión moral imposible, una traición, un sacrificio."
                )
            )

        # ── Prioridad 2: Umbrales individuales ────────────────────────────

        # Cierre de arco (precedencia sobre Plot Twist)
        if v.saturation > 95:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.ARC_CLOSURE,
                trigger_meter = "saturation",
                trigger_value = v.saturation,
                description   = (
                    "El arco narrativo actual está completamente agotado. "
                    "DEBE resolverse o cerrarse ahora. La historia entra en "
                    "un nuevo capítulo o llega a su final."
                )
            )

        # Clímax (tensión extrema)
        if v.tension > 85:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.CLIMAX,
                trigger_meter = "tension",
                trigger_value = v.tension,
                description   = (
                    "La tensión ha llegado a su punto máximo. DEBE ocurrir "
                    "una confrontación directa con el conflicto central. "
                    "No puede posponerse más."
                )
            )

        # Tragedia (esperanza al límite)
        if v.hope < 10:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.TRAGEDY,
                trigger_meter = "hope",
                trigger_value = v.hope,
                description   = (
                    "La esperanza ha colapsado. Un evento de pérdida "
                    "irreversible DEBE ocurrir, confirmando que la situación "
                    "es tan grave como parece."
                )
            )

        # Tormenta de caos
        if v.chaos > 80:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.CHAOS_STORM,
                trigger_meter = "chaos",
                trigger_value = v.chaos,
                description   = (
                    "El mundo está en caos total. Un evento externo "
                    "impredecible DEBE irrumpir, fuera del control del "
                    "protagonista."
                )
            )

        # Giro argumental (saturación alta)
        if v.saturation > 85:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.PLOT_TWIST,
                trigger_meter = "saturation",
                trigger_value = v.saturation,
                description   = (
                    "La historia necesita un giro. DEBE introducirse algo "
                    "nuevo: un personaje inesperado, una revelación, o un "
                    "cambio de escenario que renueve el conflicto."
                )
            )

        # Historia demasiado tranquila (tensión muy baja)
        if v.tension < 15:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.DISRUPTIVE,
                trigger_meter = "tension",
                trigger_value = v.tension,
                description   = (
                    "La historia está demasiado tranquila. DEBE introducirse "
                    "una nueva amenaza o conflicto que reactive el drama."
                )
            )

        # Amenaza inesperada (demasiado optimismo)
        if v.hope > 90:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.UNEXPECTED_THREAT,
                trigger_meter = "hope",
                trigger_value = v.hope,
                description   = (
                    "Todo va demasiado bien. Un problema inesperado DEBE "
                    "aparecer para evitar un final demasiado cómodo."
                )
            )

        # Descanso narrativo (ritmo sostenido alto)
        if v.rhythm > 90 and v.vector._high_rhythm_turns >= 3:
            return ForcedEventConstraint(
                event_type    = ForcedEventType.NARRATIVE_REST,
                trigger_meter = "rhythm",
                trigger_value = v.rhythm,
                description   = (
                    "El ritmo ha sido intenso por varios turnos. DEBE haber "
                    "una escena de pausa: introspección, diálogo significativo, "
                    "o un momento de calma antes de la siguiente tormenta."
                )
            )

        # Sin umbrales cruzados: la historia avanza libremente
        return None

    def get_dramatic_summary(self) -> str:
        """
        Resumen del estado dramático para incluir en el contexto de la IA.
        La IA usa esto para entender el 'clima emocional' actual.
        """
        v = self.vector
        lines = [
            "ESTADO DRAMÁTICO ACTUAL:",
            f"  Tensión:    {v.tension}/100  {'🔴' if v.tension > 70 else '🟡' if v.tension > 40 else '🟢'}",
            f"  Esperanza:  {v.hope}/100  {'🟢' if v.hope > 60 else '🟡' if v.hope > 30 else '🔴'}",
            f"  Caos:       {v.chaos}/100",
            f"  Ritmo:      {v.rhythm}/100",
            f"  Saturación: {v.saturation}/100",
            f"  Conexión:   {v.connection}/100",
            f"  Misterio:   {v.mystery}/100",
        ]
        return "\n".join(lines)

    def get_arc_analysis(self) -> dict:
        """
        Análisis del arco dramático para el paper.
        Calcula métricas sobre la curva de tensión a lo largo de la historia.
        """
        if len(self._history) < 2:
            return {"error": "Historia demasiado corta para análisis"}

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
