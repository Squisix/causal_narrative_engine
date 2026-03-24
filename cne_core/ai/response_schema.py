"""
cne_core/ai/response_schema.py - Schema de respuesta de la IA

Define el contrato JSON que la IA debe retornar usando Pydantic.
Esto garantiza que las respuestas sean válidas y puedan ser procesadas
por el motor sin errores.

Ejemplo de respuesta esperada:
{
  "narrative": "Texto inmersivo de 150-250 palabras...",
  "summary": "Resumen causal de 1 oracion",
  "choices": ["opcion A", "opcion B", "opcion C"],
  "choice_dramatic_preview": [
    {"choice": "opcion A", "tension_delta": 15, "hope_delta": -10, "tone": "confrontacional"},
    {"choice": "opcion B", "tension_delta": -5, "hope_delta": 5, "tone": "diplomatico"},
    {"choice": "opcion C", "tension_delta": 5, "hope_delta": 10, "tone": "inesperado"}
  ],
  "entity_deltas": [
    {"entity_id": "uuid", "entity_name": "Lyra", "attribute": "health", "old_value": 100, "new_value": 85}
  ],
  "world_deltas": [
    {"variable": "political_stability", "old_value": 60, "new_value": 48}
  ],
  "dramatic_deltas": {
    "tension": 15, "hope": -8, "chaos": 5,
    "rhythm": 0, "saturation": 8, "connection": -3, "mystery": 10
  },
  "causal_reason": "Por que este evento ocurre dado el estado actual",
  "forced_event_type": null,
  "is_ending": false
}
"""

from typing import Any, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class DramaticDeltaDict(BaseModel):
    """
    Cambios en el vector dramatico propuestos por la IA.

    Cada valor debe estar en rango [-100, +100].
    Un valor de 0 significa "sin cambio".
    """
    tension: int = Field(default=0, ge=-100, le=100)
    hope: int = Field(default=0, ge=-100, le=100)
    chaos: int = Field(default=0, ge=-100, le=100)
    rhythm: int = Field(default=0, ge=-100, le=100)
    saturation: int = Field(default=0, ge=-100, le=100)
    connection: int = Field(default=0, ge=-100, le=100)
    mystery: int = Field(default=0, ge=-100, le=100)

    def to_dramatic_delta(self):
        """Convierte a DramaticDelta del core."""
        from cne_core.models.event import DramaticDelta
        return DramaticDelta(
            tension=self.tension,
            hope=self.hope,
            chaos=self.chaos,
            rhythm=self.rhythm,
            saturation=self.saturation,
            connection=self.connection,
            mystery=self.mystery,
        )


class EntityDeltaDict(BaseModel):
    """
    Cambio en un atributo de una entidad.

    La IA debe especificar entity_id (UUID), entity_name (para validacion),
    el atributo que cambia, y los valores old/new.
    """
    entity_id: str = Field(..., description="UUID de la entidad")
    entity_name: str = Field(..., description="Nombre de la entidad (para validacion)")
    attribute: str = Field(..., description="Nombre del atributo que cambia")
    old_value: Any = Field(..., description="Valor anterior")
    new_value: Any = Field(..., description="Nuevo valor")

    def to_entity_delta(self):
        """Convierte a EntityDelta del core."""
        from cne_core.models.event import EntityDelta
        return EntityDelta(
            entity_id=self.entity_id,
            entity_name=self.entity_name,
            attribute=self.attribute,
            old_value=self.old_value,
            new_value=self.new_value,
        )


class WorldDeltaDict(BaseModel):
    """
    Cambio en una variable global del mundo.
    """
    variable: str = Field(..., description="Nombre de la variable")
    old_value: Any = Field(..., description="Valor anterior")
    new_value: Any = Field(..., description="Nuevo valor")

    def to_world_delta(self):
        """Convierte a WorldVariableDelta del core."""
        from cne_core.models.event import WorldVariableDelta
        return WorldVariableDelta(
            variable=self.variable,
            old_value=self.old_value,
            new_value=self.new_value,
        )


class ChoicePreview(BaseModel):
    """
    Preview del impacto dramatico estimado de una opcion.

    Esto ayuda al jugador a entender las consecuencias potenciales
    de cada decision antes de tomarla.
    """
    choice: str = Field(..., description="Texto de la opcion")
    tension_delta: int = Field(default=0, ge=-50, le=50, description="Cambio estimado en tension")
    hope_delta: int = Field(default=0, ge=-50, le=50, description="Cambio estimado en esperanza")
    chaos_delta: int = Field(default=0, ge=-50, le=50, description="Cambio estimado en caos")
    tone: str = Field(default="neutral", description="Tono de la opcion (confrontacional, diplomatico, etc.)")

    def to_narrative_choice(self):
        """Convierte a NarrativeChoice del core."""
        from cne_core.models.commit import NarrativeChoice
        return NarrativeChoice(
            text=self.choice,
            dramatic_preview={
                "tension": self.tension_delta,
                "hope": self.hope_delta,
                "chaos": self.chaos_delta,
            },
            tone_hint=self.tone,
        )


class NarrativeResponse(BaseModel):
    """
    Respuesta completa de la IA.

    Este es el schema que la IA debe seguir obligatoriamente.
    El ResponseValidator verificara que todo sea coherente antes
    de aplicarlo al motor.
    """
    # Narrativa
    narrative: str = Field(
        ...,
        min_length=50,
        max_length=2000,
        description="Texto narrativo inmersivo (150-250 palabras recomendado)"
    )

    summary: str = Field(
        ...,
        min_length=10,
        max_length=200,
        description="Resumen causal de 1 oracion para el tronco activo"
    )

    # Opciones del jugador
    choices: list[str] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="Opciones disponibles para el jugador (2-5 opciones)"
    )

    choice_dramatic_preview: list[ChoicePreview] = Field(
        default_factory=list,
        description="Preview del impacto de cada opcion"
    )

    # Deltas de estado
    entity_deltas: list[EntityDeltaDict] = Field(
        default_factory=list,
        description="Cambios en entidades causados por este evento"
    )

    world_deltas: list[WorldDeltaDict] = Field(
        default_factory=list,
        description="Cambios en variables globales del mundo"
    )

    dramatic_deltas: DramaticDeltaDict = Field(
        default_factory=DramaticDeltaDict,
        description="Cambios en el vector dramatico"
    )

    # Metadata
    causal_reason: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Por que este evento ocurre dado el estado actual"
    )

    forced_event_type: Optional[str] = Field(
        default=None,
        description="Si hay un evento forzado, su tipo (CLIMAX, TRAGEDY, etc.)"
    )

    is_ending: bool = Field(
        default=False,
        description="¿Es este el final de la historia?"
    )

    @field_validator('choice_dramatic_preview')
    @classmethod
    def validate_preview_matches_choices(cls, v, info):
        """Verifica que haya un preview para cada choice."""
        if 'choices' in info.data:
            choices = info.data['choices']
            if len(v) > 0 and len(v) != len(choices):
                raise ValueError(
                    f"Debe haber {len(choices)} previews, uno por cada opcion. "
                    f"Encontrados: {len(v)}"
                )
            # Verificar que los textos coincidan
            if v:
                preview_texts = {p.choice for p in v}
                choice_texts = set(choices)
                if preview_texts != choice_texts:
                    raise ValueError(
                        f"Los textos de las opciones no coinciden entre choices y preview"
                    )
        return v

    @field_validator('narrative')
    @classmethod
    def validate_narrative_length(cls, v):
        """Verifica que la narrativa tenga una longitud razonable."""
        word_count = len(v.split())
        if word_count < 30:
            raise ValueError(
                f"La narrativa es demasiado corta ({word_count} palabras). "
                f"Minimo recomendado: 50 palabras."
            )
        if word_count > 400:
            raise ValueError(
                f"La narrativa es demasiado larga ({word_count} palabras). "
                f"Maximo recomendado: 250 palabras."
            )
        return v

    @field_validator('is_ending')
    @classmethod
    def validate_ending_has_no_choices(cls, v, info):
        """Si es el final, no debe haber opciones."""
        if v and 'choices' in info.data:
            choices = info.data['choices']
            if len(choices) > 0:
                raise ValueError(
                    "Si is_ending=true, no debe haber choices. "
                    "El final no tiene mas decisiones."
                )
        return v

    def to_core_models(self):
        """
        Convierte la respuesta a los modelos del core.

        Returns:
            tuple: (entity_deltas, world_deltas, dramatic_delta, choices)
        """
        entity_deltas = [d.to_entity_delta() for d in self.entity_deltas]
        world_deltas = [d.to_world_delta() for d in self.world_deltas]
        dramatic_delta = self.dramatic_deltas.to_dramatic_delta()

        # Si hay previews, usarlos. Si no, crear choices sin preview
        if self.choice_dramatic_preview:
            choices = [p.to_narrative_choice() for p in self.choice_dramatic_preview]
        else:
            from cne_core.models.commit import NarrativeChoice
            choices = [NarrativeChoice(text=c) for c in self.choices]

        return entity_deltas, world_deltas, dramatic_delta, choices

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "narrative": "La sala del trono esta en silencio cuando Lyra recibe la noticia...",
                "summary": "El rey Aldric muere misteriosamente. Lyra asume el trono.",
                "choices": [
                    "Confrontar a Malachar directamente",
                    "Ordenar una investigacion secreta",
                    "Aceptar la 'ayuda' de Malachar"
                ],
                "choice_dramatic_preview": [
                    {
                        "choice": "Confrontar a Malachar directamente",
                        "tension_delta": 15,
                        "hope_delta": -5,
                        "tone": "confrontacional"
                    },
                    {
                        "choice": "Ordenar una investigacion secreta",
                        "tension_delta": 5,
                        "hope_delta": 5,
                        "tone": "cauteloso"
                    },
                    {
                        "choice": "Aceptar la 'ayuda' de Malachar",
                        "tension_delta": -5,
                        "hope_delta": -10,
                        "tone": "sumiso"
                    }
                ],
                "entity_deltas": [],
                "world_deltas": [],
                "dramatic_deltas": {
                    "tension": 10,
                    "hope": -5,
                    "chaos": 5,
                    "rhythm": 0,
                    "saturation": 2,
                    "connection": 5,
                    "mystery": 10
                },
                "causal_reason": "La muerte del rey es el evento desencadenante que inicia el conflicto",
                "forced_event_type": None,
                "is_ending": False
            }
        }
    )
