"""
models/commit.py — Versionado tipo Git del árbol narrativo

Un NarrativeCommit es como un commit de Git:
- Tiene un parent (el commit anterior)
- Registra qué decisión se tomó
- Guarda el estado del mundo en ese momento
- Puede ramificarse (un commit puede tener múltiples hijos)

Esto es lo que hace posible:
- Volver atrás en la historia
- Explorar ramas alternativas
- Comparar qué hubiera pasado con otra decisión
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
import uuid


# ── NarrativeCommit ───────────────────────────────────────────────────────────

@dataclass
class NarrativeCommit:
    """
    Un punto en la historia. Equivalente a un commit de Git.

    La historia no se guarda como texto lineal, sino como una cadena
    de commits. Cada commit apunta a su padre (parent_id), formando
    un árbol que puede ramificarse.

    Ejemplo de árbol:
        commit_0 (inicio)
            └─ commit_1 (decisión: "hablar con el rey")
                ├─ commit_2a (decisión: "aceptar la misión")  ← rama A
                └─ commit_2b (decisión: "rechazar la misión") ← rama B

    Attributes:
        world_id:        A qué WorldDefinition pertenece.
        parent_id:       El commit anterior. None solo para el primero.
        event_id:        El NarrativeEvent que generó este commit.
        choice_text:     La decisión en texto (lo que eligió el jugador).
        narrative_text:  El texto narrativo completo de este momento.
        summary:         Resumen de 1 oración (para comprimir el tronco).
        depth:           Cuántas decisiones se han tomado hasta aquí.
        branch_id:       Identificador de la rama en la que estamos.
        dramatic_snapshot: Estado del DramaticVector en este commit.
        world_state_snapshot: Estado de las variables globales del mundo.
        entity_states:   Estado de las entidades en este commit.
        is_ending:       ¿Es el final de la historia?
        children_ids:    IDs de los commits hijos (ramas alternativas).
    """
    world_id:      str
    event_id:      str
    depth:         int

    parent_id:     str | None     = None   # None solo en el commit raíz
    choice_text:   str | None     = None   # None en el commit inicial
    narrative_text: str           = ""
    summary:       str            = ""

    branch_id:     str            = field(default_factory=lambda: str(uuid.uuid4()))

    # Estado del mundo en este commit (snapshot ligero)
    dramatic_snapshot:    dict[str, int]  = field(default_factory=dict)
    world_state_snapshot: dict[str, Any]  = field(default_factory=dict)
    entity_states:        dict[str, Any]  = field(default_factory=dict)

    is_ending:     bool           = False
    children_ids:  list[str]      = field(default_factory=list)

    id:            str            = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:    datetime       = field(default_factory=datetime.now)

    @property
    def is_root(self) -> bool:
        """¿Es el primer commit de la historia?"""
        return self.parent_id is None

    @property
    def has_branches(self) -> bool:
        """¿Tiene múltiples caminos desde aquí?"""
        return len(self.children_ids) > 1

    def add_child(self, child_id: str) -> None:
        """Registra un commit hijo (cuando el jugador toma una decisión aquí)."""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)

    def get_dramatic_meter(self, meter: str) -> int:
        """Acceso seguro a un medidor del snapshot dramático."""
        return self.dramatic_snapshot.get(meter, 0)

    def to_trunk_entry(self) -> str:
        """
        Representación compacta para el tronco activo.
        Los commits lejanos se incluyen en el contexto de la IA
        con esta representación de una sola línea.
        """
        prefix = ""
        if self.choice_text:
            prefix = f'-> "{self.choice_text}" | '

        tension = self.get_dramatic_meter("tension")
        hope    = self.get_dramatic_meter("hope")

        return (
            f"[Cap.{self.depth}] {prefix}{self.summary} "
            f"(tension={tension}, esperanza={hope})"
        )

    def __str__(self) -> str:
        choice = f'"{self.choice_text}"' if self.choice_text else "inicio"
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
    Metadatos de una rama del árbol narrativo.

    Una rama es una secuencia de commits desde un punto de divergencia
    hasta la hoja actual (o un final). Cuando el jugador vuelve atrás
    y toma una decisión diferente, se crea una nueva rama.

    El branch_id se propaga a todos los commits de esa rama.
    """
    world_id:      str
    origin_commit_id: str    # Desde qué commit se divergió
    name:          str       = "Rama principal"
    description:   str       = ""
    leaf_commit_id: str | None = None   # El commit más reciente de esta rama

    id:            str       = field(default_factory=lambda: str(uuid.uuid4()))
    created_at:    datetime  = field(default_factory=datetime.now)

    def __str__(self) -> str:
        return f"Branch('{self.name}', origin={self.origin_commit_id[:8]}...)"


# ── NarrativeChoice ───────────────────────────────────────────────────────────

@dataclass
class NarrativeChoice:
    """
    Una opción disponible para el jugador en un momento dado.

    Las hojas del árbol literario. La IA las genera, el motor las valida
    y las presenta. El jugador elige una → nuevo commit → nueva rama si
    ya había un commit hijo en este punto.

    dramatic_preview muestra cómo ESTIMAMOS que cambiará el vector
    dramático si se elige esta opción. Es una predicción de la IA,
    no una garantía del motor.
    """
    text:             str                    # El texto de la opción
    dramatic_preview: dict[str, int]         = field(default_factory=dict)
    tone_hint:        str                    = ""   # "confrontacional", "diplomático", etc.
    estimated_depth_until_ending: int | None = None

    def get_preview_str(self) -> str:
        """Resumen del impacto dramático estimado para mostrar al jugador."""
        if not self.dramatic_preview:
            return ""
        parts = []
        for meter, delta in self.dramatic_preview.items():
            if delta != 0:
                sign  = "+" if delta > 0 else ""
                arrow = "^" if delta > 0 else "v"
                parts.append(f"{arrow}{meter}{sign}{delta}")
        return "  ".join(parts[:3])   # Mostrar máximo 3 para no saturar la UI

    def __str__(self) -> str:
        return f"NarrativeChoice('{self.text[:40]}...')"
