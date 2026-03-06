"""
models/world.py — La Semilla del Árbol Literario

En Python, @dataclass genera automáticamente __init__, __repr__ y __eq__
a partir de los campos que defines. Es equivalente a un 'data class' en
Kotlin, un 'record' en Java 17+, o una 'struct' en Go.

field(default_factory=...) se usa para valores por defecto que son
objetos mutables (listas, dicts). En Python nunca pongas [] o {} como
default directo en una dataclass — se compartiría entre instancias.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import uuid


# ── Enums ─────────────────────────────────────────────────────────────────────

class EntityType(str, Enum):
    """
    str + Enum: el valor es una string serializable directamente a JSON.
    Útil cuando persistamos o mandemos datos a la IA.
    """
    CHARACTER = "character"
    FACTION   = "faction"
    ARTIFACT  = "artifact"
    LOCATION  = "location"


class NarrativeTone(str, Enum):
    EPIC        = "épico"
    DARK        = "oscuro"
    MYSTERIOUS  = "misterioso"
    ADVENTUROUS = "aventurero"
    PHILOSOPHICAL = "filosófico"
    BLACK_HUMOR = "humor_negro"


# ── Entity ────────────────────────────────────────────────────────────────────

@dataclass
class Entity:
    """
    Una entidad persistente del mundo narrativo.

    El motor NUNCA borra entidades — solo las marca como destruidas.
    Esto preserva la historia completa y permite reconstruir cualquier
    estado pasado.

    Attributes:
        id:           Identificador único. uuid4() genera uno aleatorio.
        name:         Nombre del personaje/objeto/lugar.
        entity_type:  Qué tipo de entidad es (ver EntityType).
        attributes:   Dict flexible para cualquier atributo del mundo.
                      Ej: {"alive": True, "health": 100, "loyalty": 80}
        created_at_depth: En qué profundidad narrativa fue creada.
        destroyed_at_depth: None si está viva, número si fue destruida.
    """
    name:        str
    entity_type: EntityType
    attributes:  dict[str, Any]       = field(default_factory=dict)
    id:          str                  = field(default_factory=lambda: str(uuid.uuid4()))
    created_at_depth:    int          = 0
    destroyed_at_depth:  int | None   = None   # None = viva

    @property
    def is_alive(self) -> bool:
        """
        Una property en Python es un método que se accede como atributo.
        entity.is_alive  →  llama a este getter automáticamente.
        """
        # Si destroyed_at_depth es None, la entidad sigue viva
        return self.destroyed_at_depth is None

    def get_attr(self, key: str, default: Any = None) -> Any:
        """Acceso seguro a atributos con valor por defecto."""
        return self.attributes.get(key, default)

    def __str__(self) -> str:
        status = "✓" if self.is_alive else "✗"
        return f"[{status}] {self.name} ({self.entity_type.value})"


# ── WorldDefinition (La Semilla) ──────────────────────────────────────────────

@dataclass
class WorldDefinition:
    """
    La Semilla — inmutable una vez creada.

    Define el espacio de estados posibles de la historia. La IA siempre
    recibe esta definición como parte del contexto. Las reglas aquí son
    el 'contrato narrativo': ni la IA ni el jugador pueden violarlas.

    Attributes:
        name:           Nombre del mundo/historia.
        context:        Descripción detallada del universo narrativo.
        protagonist:    Nombre y descripción del personaje principal.
        era:            Época/ambientación (ej: "Medieval fantástico, año 843").
        tone:           Tono narrativo general.
        antagonist:     Conflicto o antagonista central.
        rules:          Reglas del mundo (ej: "La magia existe pero tiene precio").
        constraints:    Lista de cosas PROHIBIDAS narrativamente.
                        El motor y la IA deben respetar estas restricciones.
        initial_entities: Personajes/objetos/lugares que existen desde el inicio.
        dramatic_config:  Configuración inicial del vector dramático.
        max_depth:      Máximo de decisiones antes de forzar un final.
                        0 = ilimitado.
        id:             UUID generado automáticamente.
        created_at:     Timestamp de creación.
    """
    name:       str
    context:    str
    protagonist: str
    era:        str
    tone:       NarrativeTone

    antagonist:  str              = "desconocido"
    rules:       str              = "El mundo sigue sus propias leyes"
    constraints: list[str]        = field(default_factory=list)

    # Entidades iniciales del mundo
    initial_entities: list[Entity] = field(default_factory=list)

    # Configuración dramática: valores iniciales de cada medidor [0-100]
    # El motor usará estos como punto de partida del DramaticVector
    dramatic_config: dict[str, int] = field(default_factory=lambda: {
        "tension":    30,
        "hope":       60,
        "chaos":      20,
        "rhythm":     50,
        "saturation": 0,
        "connection": 40,
        "mystery":    50,
    })

    max_depth: int  = 0   # 0 = sin límite

    id:         str       = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime  = field(default_factory=datetime.now)

    def get_entity_by_name(self, name: str) -> Entity | None:
        """Busca una entidad inicial por nombre. Retorna None si no existe."""
        for entity in self.initial_entities:
            if entity.name.lower() == name.lower():
                return entity
        return None

    def to_context_string(self) -> str:
        """
        Serializa la semilla a texto para enviar a la IA.
        Este es el bloque que siempre estará presente en el tronco activo.
        """
        lines = [
            f"MUNDO: {self.name}",
            f"CONTEXTO: {self.context}",
            f"PROTAGONISTA: {self.protagonist}",
            f"ÉPOCA: {self.era}",
            f"TONO: {self.tone.value}",
            f"ANTAGONISTA/CONFLICTO: {self.antagonist}",
            f"REGLAS DEL MUNDO: {self.rules}",
        ]

        if self.constraints:
            lines.append("RESTRICCIONES ABSOLUTAS:")
            for c in self.constraints:
                lines.append(f"  - {c}")

        if self.initial_entities:
            lines.append("ENTIDADES INICIALES:")
            for e in self.initial_entities:
                attrs_str = ", ".join(f"{k}={v}" for k, v in e.attributes.items())
                lines.append(f"  - {e.name} ({e.entity_type.value}): {attrs_str}")

        return "\n".join(lines)

    def __str__(self) -> str:
        return f"WorldDefinition('{self.name}', tono={self.tone.value}, entidades={len(self.initial_entities)})"
