"""
adapters/mock_adapter.py - Mock AIAdapter para tests

Este adapter NO usa una IA real. Genera respuestas deterministas
basadas en plantillas predefinidas.

Util para:
- Tests que no requieren API keys
- Desarrollo local sin costos de API
- CI/CD que no tiene acceso a secrets
- Validar el flujo del motor sin depender de IA externa
"""

import json
import random
from typing import Optional

from cne_core.interfaces.ai_adapter import AIAdapter, NarrativeContext, NarrativeProposal
from cne_core.ai.response_schema import (
    NarrativeResponse,
    ChoicePreview,
    DramaticDeltaDict,
    EntityDeltaDict,
    WorldDeltaDict,
)


class MockAdapter(AIAdapter):
    """
    Mock AIAdapter que genera respuestas deterministas.

    Las respuestas son genericas pero validas, y puedes controlar
    su comportamiento con parametros.
    """

    def __init__(
        self,
        deterministic: bool = True,
        seed: int = 42,
        force_errors: bool = False,
    ):
        """
        Args:
            deterministic: Si True, siempre genera la misma respuesta para el mismo input.
            seed: Semilla para generacion pseudoaleatoria (si no es deterministic).
            force_errors: Si True, genera respuestas invalidas para testing.
        """
        self.deterministic = deterministic
        self.seed = seed
        self.force_errors = force_errors
        self.call_count = 0

        if not deterministic:
            random.seed(seed)

    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal:
        """
        Genera una narrativa mock basada en el contexto.

        La narrativa es generica pero coherente con el estado del mundo.
        """
        self.call_count += 1

        # Si estamos forzando errores, generar respuesta invalida
        if self.force_errors:
            return self._generate_invalid_response(context)

        # Generar respuesta valida
        return self._generate_valid_response(context)

    def _generate_valid_response(self, context: NarrativeContext) -> NarrativeProposal:
        """Genera una respuesta valida usando plantillas."""

        # Determinar si es el inicio de la historia
        is_start = context.current_depth == 0
        is_forced = context.forced_constraint is not None

        # Plantillas de narrativa
        if is_start:
            narrative = self._generate_start_narrative(context)
        elif is_forced:
            narrative = self._generate_forced_narrative(context)
        else:
            narrative = self._generate_normal_narrative(context)

        # Generar summary
        summary = self._generate_summary(context, is_start, is_forced)

        # Generar choices (2-4 opciones)
        num_choices = 3 if self.deterministic else random.randint(2, 4)
        choices, choice_previews = self._generate_choices(context, num_choices)

        # Generar deltas dramaticos (basados en el contexto)
        dramatic_deltas = self._generate_dramatic_deltas(context, is_forced)

        # Entity y world deltas (vacios en el mock simple)
        entity_deltas = []
        world_deltas = []

        # Causal reason
        causal_reason = self._generate_causal_reason(context, is_start)

        # Construir respuesta
        response = NarrativeResponse(
            narrative=narrative,
            summary=summary,
            choices=choices,
            choice_dramatic_preview=choice_previews,
            entity_deltas=entity_deltas,
            world_deltas=world_deltas,
            dramatic_deltas=dramatic_deltas,
            causal_reason=causal_reason,
            forced_event_type=context.forced_constraint.event_type.value if is_forced else None,
            is_ending=False,
        )

        # Convertir a NarrativeProposal
        entity_deltas_core, world_deltas_core, dramatic_delta_core, choices_core = response.to_core_models()

        return NarrativeProposal(
            narrative_text=response.narrative,
            summary=response.summary,
            choices=choices_core,
            entity_deltas=entity_deltas_core,
            world_deltas=world_deltas_core,
            dramatic_delta=dramatic_delta_core,
            causal_reason=response.causal_reason,
            is_ending=response.is_ending,
            raw_response=response.model_dump(),
        )

    def _generate_start_narrative(self, context: NarrativeContext) -> str:
        """Genera narrativa de inicio."""
        world_name = context.world_definition.name
        protagonist = context.world_definition.protagonist
        tone = context.world_definition.tone.value

        return f"""La historia de {world_name} comienza. {protagonist} se encuentra en un momento crucial. El ambiente es {tone}, y las decisiones que tome ahora determinaran el curso de los eventos venideros. Todo esta en calma, pero se siente la tension en el aire. Es el momento de actuar."""

    def _generate_forced_narrative(self, context: NarrativeContext) -> str:
        """Genera narrativa para evento forzado."""
        event_type = context.forced_constraint.event_type.value
        description = context.forced_constraint.description

        return f"""[EVENTO FORZADO: {event_type}] {description} La situacion ha alcanzado un punto critico. No hay vuelta atras. Los eventos que llevaron a este momento culminan ahora en una confrontacion directa con las fuerzas en juego. La tension es palpable, y las consecuencias de lo que suceda a continuacion resonaran a traves de toda la historia."""

    def _generate_normal_narrative(self, context: NarrativeContext) -> str:
        """Genera narrativa normal."""
        choice_text = context.player_choice if context.player_choice else "una decision"

        narratives = [
            f"""Habiendo elegido {choice_text}, los acontecimientos se desarrollan de forma inesperada. La decision tomada tiene ramificaciones que se extienden mas alla de lo inmediatamente visible. Nuevas oportunidades se abren, pero tambien nuevos peligros acechan en las sombras. Es momento de considerar cuidadosamente el proximo paso.""",

            f"""La eleccion de {choice_text} reverbera a traves de los eventos. Las consecuencias se manifiestan de formas sutiles y evidentes. Algunos caminos se cierran mientras otros se revelan. La historia avanza, llevando consigo el peso de las decisiones pasadas y la promesa de las futuras.""",

            f"""Tras {choice_text}, el mundo responde. Los ecos de esta accion se extienden, tocando vidas y alterando destinos. Lo que parecia claro ahora se torna complejo. Nuevas preguntas emergen, demandando atencion. El camino adelante requiere sabiduria y coraje.""",
        ]

        if self.deterministic:
            return narratives[self.call_count % len(narratives)]
        else:
            return random.choice(narratives)

    def _generate_summary(self, context: NarrativeContext, is_start: bool, is_forced: bool) -> str:
        """Genera un summary de 1 linea."""
        if is_start:
            return f"La historia de {context.world_definition.name} comienza."

        if is_forced:
            event_type = context.forced_constraint.event_type.value
            return f"Evento forzado: {event_type} ocurre como consecuencia de las decisiones previas."

        choice = context.player_choice if context.player_choice else "una accion"
        return f"Tras {choice}, nuevos eventos se desarrollan y opciones emergen."

    def _generate_choices(self, context: NarrativeContext, num: int) -> tuple[list[str], list[ChoicePreview]]:
        """Genera opciones y sus previews."""
        choice_templates = [
            ("Actuar con cautela y observar", 5, 5, 0, "cauteloso"),
            ("Tomar accion directa e inmediata", 15, -5, 5, "confrontacional"),
            ("Buscar aliados antes de proceder", 5, 10, -5, "diplomatico"),
            ("Explorar alternativas no obvias", 10, 0, 10, "creativo"),
            ("Esperar y recopilar mas informacion", -5, 5, -10, "paciente"),
        ]

        selected = choice_templates[:num]
        choices = [c[0] for c in selected]
        previews = [
            ChoicePreview(
                choice=c[0],
                tension_delta=c[1],
                hope_delta=c[2],
                chaos_delta=c[3],
                tone=c[4],
            )
            for c in selected
        ]

        return choices, previews

    def _generate_dramatic_deltas(self, context: NarrativeContext, is_forced: bool) -> DramaticDeltaDict:
        """Genera deltas dramaticos basados en el contexto."""
        if is_forced:
            # Evento forzado: impacto grande
            event_type = context.forced_constraint.event_type.value
            if event_type == "CLIMAX":
                return DramaticDeltaDict(tension=25, hope=-10, saturation=20)
            elif event_type == "TRAGEDY":
                return DramaticDeltaDict(tension=15, hope=-30, connection=-10)
            else:
                return DramaticDeltaDict(tension=10, hope=-5, chaos=10)
        else:
            # Evento normal: impacto moderado
            return DramaticDeltaDict(
                tension=5,
                hope=0,
                chaos=2,
                saturation=3,
            )

    def _generate_causal_reason(self, context: NarrativeContext, is_start: bool) -> str:
        """Genera la razon causal."""
        if is_start:
            return "Este es el evento inicial que establece el estado del mundo."

        if context.player_choice:
            return f"Este evento ocurre como consecuencia directa de la decision: {context.player_choice}"

        return "Este evento es una continuacion natural de los acontecimientos previos."

    def _generate_invalid_response(self, context: NarrativeContext) -> NarrativeProposal:
        """Genera una respuesta invalida para testing de error handling."""
        # Crear una respuesta invalida SIN usar Pydantic (para bypassear validacion)
        # Esto simula lo que pasaria si la IA retorna JSON invalido
        from cne_core.models.event import DramaticDelta

        return NarrativeProposal(
            narrative_text="Muy corto",  # Demasiado corto, < 50 caracteres
            summary="X",  # Demasiado corto, < 10 caracteres
            choices=[],  # Sin choices (invalido)
            entity_deltas=[],
            world_deltas=[],
            dramatic_delta=DramaticDelta(tension=0, hope=0, chaos=0),
            causal_reason="Error forced",
            is_ending=False,
            raw_response={"error": "forced_error_mode"},
        )

    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        """
        Valida y parsea la respuesta (no usado en mock, siempre retorna mock data).

        En un adapter real, esto parsearia JSON y validaria con Pydantic.
        En el mock, simplemente genera una respuesta mock.
        """
        # El mock no usa raw_response, genera directamente
        # Este metodo existe solo para cumplir con la interfaz
        return await self._generate_valid_response(
            NarrativeContext(
                world_definition=None,  # No usado en mock validation
                current_depth=0,
                current_dramatic_state={},
                current_entity_states={},
                current_world_vars={},
                commit_chain=[],
                player_choice=None,
                forced_constraint=None,
            )
        )

    def get_model_info(self) -> dict[str, str]:
        """Retorna informacion del modelo (mock)."""
        return {
            "provider": "Mock",
            "model": "Deterministic" if self.deterministic else "Random",
            "version": f"seed-{self.seed}",
        }

    def get_stats(self) -> dict:
        """Retorna estadisticas del mock adapter."""
        return {
            "total_calls": self.call_count,
            "deterministic": self.deterministic,
            "force_errors": self.force_errors,
        }
