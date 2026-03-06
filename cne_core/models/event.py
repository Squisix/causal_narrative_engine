"""
models/event.py — Eventos y el Grafo Causal

Un NarrativeEvent es la unidad atómica del motor.
Cada cosa que pasa en la historia es un evento: una batalla,
una conversación, una muerte, un descubrimiento.

Los eventos se conectan entre sí formando un DAG (Directed Acyclic Graph):
    muerte_del_rey → guerra_civil → invasión_extranjera

La restricción DAG (sin ciclos) es lo que garantiza que la historia
sea causalmente coherente: ningún evento puede ser causa de sí mismo.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class EventType(str, Enum):
    """Tipos de eventos que puede procesar el motor."""
    DECISION    = "decision"     # Acción tomada por el jugador
    CONSEQUENCE = "consequence"  # Consecuencia directa de una decisión
    FORCED      = "forced"       # Evento forzado por el DramaticEngine (umbrales)
    CLIMAX      = "climax"       # Clímax narrativo forzado
    REVELATION  = "revelation"   # Revelación de misterio
    ENDING      = "ending"       # Final de la historia


class CausalRelationType(str, Enum):
    """
    Tipo de relación causal entre dos eventos.
    Útil para el paper y para que la IA comprenda el grafo.
    """
    DIRECT      = "direct"       # A causó directamente B
    ENABLES     = "enables"      # A hizo posible B
    TRIGGERS    = "triggers"     # A detonó B (con cierto delay)
    PREVENTS    = "prevents"     # A impidió que ocurriera C (negativo)
    AMPLIFIES   = "amplifies"    # A hizo B más intenso


# ── Deltas de estado ──────────────────────────────────────────────────────────

@dataclass
class EntityDelta:
    """
    Representa el cambio en un atributo de una entidad.

    Ejemplo: hero.health cambia de 100 a 90.
        entity_id = "uuid-del-hero"
        attribute = "health"
        old_value = 100
        new_value = 90

    Guardamos old_value Y new_value para poder:
    - Reconstruir el estado en cualquier dirección
    - Detectar inconsistencias
    - Generar el historial legible para la IA
    """
    entity_id:  str
    entity_name: str      # Para legibilidad en logs y contexto IA
    attribute:  str
    old_value:  Any
    new_value:  Any

    @property
    def delta_summary(self) -> str:
        """Resumen legible para incluir en el contexto de la IA."""
        return f"{self.entity_name}.{self.attribute}: {self.old_value} → {self.new_value}"


@dataclass
class WorldVariableDelta:
    """
    Cambio en una variable global del mundo.

    Ejemplo: political_stability baja de 60 a 45.
    """
    variable:  str
    old_value: Any
    new_value: Any

    @property
    def delta_summary(self) -> str:
        return f"mundo.{self.variable}: {self.old_value} → {self.new_value}"


@dataclass
class DramaticDelta:
    """
    Cambio en el vector dramático causado por este evento.

    El DramaticEngine aplica estos deltas DESPUÉS de que el evento
    es validado y antes de que se persista el commit.
    """
    tension:    int = 0
    hope:       int = 0
    chaos:      int = 0
    rhythm:     int = 0
    saturation: int = 0
    connection: int = 0
    mystery:    int = 0

    def is_empty(self) -> bool:
        """¿Este delta no cambia nada?"""
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
        return ", ".join(parts) if parts else "sin cambios dramáticos"


# ── NarrativeEvent ────────────────────────────────────────────────────────────

@dataclass
class NarrativeEvent:
    """
    La unidad atómica del motor narrativo.

    Un evento representa algo que sucedió en la historia, con:
    - Su narrativa (el texto que ve el jugador)
    - Sus causas (qué eventos previos lo hicieron posible)
    - Sus efectos (qué cambia en el mundo)
    - Su impacto dramático (cómo mueve los medidores)

    Invariante crítico: caused_by solo puede contener IDs de eventos
    anteriores (depth menor). Esto garantiza el DAG sin ciclos.
    """
    commit_id:       str           # A qué commit narrativo pertenece
    event_type:      EventType
    narrative_text:  str           # El texto que ve el jugador
    summary:         str           # Resumen de 1 oración para el tronco activo

    # Grafo causal: IDs de los eventos que causaron este
    # Si está vacío, es un evento inicial (raíz del DAG)
    caused_by:       list[str]     = field(default_factory=list)

    # Qué decisión del jugador lo disparó (None si fue forzado)
    triggered_by_decision: str | None = None

    # Los efectos del evento sobre el mundo
    entity_deltas:   list[EntityDelta]        = field(default_factory=list)
    world_deltas:    list[WorldVariableDelta]  = field(default_factory=list)
    dramatic_delta:  DramaticDelta            = field(default_factory=DramaticDelta)

    # Si es un evento FORCED, qué medidor lo disparó
    forced_by_meter: str | None    = None

    # Metadatos
    id:         str      = field(default_factory=lambda: str(uuid.uuid4()))
    depth:      int      = 0       # Profundidad narrativa en que ocurrió
    created_at: datetime = field(default_factory=datetime.now)

    # Para el paper: orden topológico en el DAG
    # Un evento hijo siempre tiene topo_order > que sus padres
    topo_order: int = 0

    def is_root(self) -> bool:
        """¿Es un evento raíz (sin causas previas)?"""
        return len(self.caused_by) == 0

    def affects_entity(self, entity_id: str) -> bool:
        """¿Este evento modifica a la entidad dada?"""
        return any(d.entity_id == entity_id for d in self.entity_deltas)

    def get_summary_for_context(self) -> str:
        """
        Retorna una representación compacta para incluir en el tronco activo.
        Los eventos lejanos se comprimen a esta forma para ahorrar tokens.
        """
        prefix = ""
        if self.triggered_by_decision:
            prefix = f'[Decisión: "{self.triggered_by_decision}"] '
        elif self.forced_by_meter:
            prefix = f"[Evento forzado por {self.forced_by_meter}] "

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
    Una arista del grafo causal: evento A causó evento B.

    El CausalValidator usa estas aristas para detectar ciclos.
    Antes de crear una arista A→B, verifica que NO exista
    un camino de B→A (lo que crearía un ciclo).

    Para el paper: la relación_type permite analizar el tipo de
    causalidad predominante en diferentes géneros narrativos.
    """
    cause_event_id:  str    # El evento que causó
    effect_event_id: str    # El evento causado

    relation_type:   CausalRelationType = CausalRelationType.DIRECT
    strength:        float              = 1.0   # [0.0 - 1.0] fuerza causal

    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __str__(self) -> str:
        return (
            f"CausalEdge({self.cause_event_id[:8]}... "
            f"→{self.relation_type.value}→ "
            f"{self.effect_event_id[:8]}...)"
        )
