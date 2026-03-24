"""
adapters/anthropic_adapter.py - Implementacion con Anthropic API (Claude)

Este adapter usa Claude (Anthropic) para generar narrativa real.

Requiere:
- pip install anthropic
- API key: ANTHROPIC_API_KEY en variable de entorno o config

Modelos recomendados:
- claude-3-5-sonnet-20241022 (mejor balance calidad/precio)
- claude-opus-4 (maxima calidad, mas caro)
- claude-haiku-3 (rapido y economico, para prototipos)
"""

import json
import os
from typing import Optional
import asyncio

try:
    import anthropic
    from anthropic import AsyncAnthropic
except ImportError:
    raise ImportError(
        "El paquete 'anthropic' no esta instalado.\n"
        "Instalalo con: pip install anthropic"
    )

from cne_core.interfaces.ai_adapter import AIAdapter, NarrativeContext, NarrativeProposal
from cne_core.ai.response_schema import NarrativeResponse
from cne_core.ai.context_builder import ContextBuilder
from cne_core.ai.response_validator import ResponseValidator, ValidationLogger


class AnthropicAdapter(AIAdapter):
    """
    AIAdapter que usa Claude (Anthropic) para generar narrativa.

    Maneja:
    - Construccion de prompts optimizados
    - Llamadas a la API de Anthropic
    - Retry logic con exponential backoff
    - Validacion de respuestas
    - Logging de errores
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = 2048,
        temperature: float = 0.7,
        max_retries: int = 3,
        timeout: float = 60.0,
    ):
        """
        Args:
            api_key: API key de Anthropic. Si None, se lee de ANTHROPIC_API_KEY env var.
            model: Modelo de Claude a usar.
            max_tokens: Maximo de tokens a generar.
            temperature: Temperatura para generacion (0.0-1.0).
            max_retries: Intentos maximos si hay error de API.
            timeout: Timeout en segundos para llamadas a API.
        """
        # API key
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key no encontrada. Provee api_key o setea ANTHROPIC_API_KEY env var."
            )

        # Cliente async
        self.client = AsyncAnthropic(api_key=self.api_key, timeout=timeout)

        # Configuracion
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries

        # Componentes
        self.context_builder = ContextBuilder()
        self.validation_logger = ValidationLogger()

        # Stats
        self.total_calls = 0
        self.total_tokens_used = 0
        self.failed_calls = 0

    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal:
        """
        Genera narrativa usando Claude.

        Args:
            context: Contexto narrativo con toda la informacion necesaria.

        Returns:
            NarrativeProposal con la narrativa generada.

        Raises:
            Exception: Si falla despues de max_retries intentos.
        """
        self.total_calls += 1

        # 1. Construir el prompt completo
        prompt = self._build_prompt(context)

        # 2. Llamar a Claude con retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                response_text = await self._call_claude(prompt)

                # 3. Parsear respuesta JSON
                response = self._parse_response(response_text)

                # 4. Validar respuesta
                validator = ResponseValidator(
                    world=context.world_definition,
                    current_entities=context.current_entity_states,
                    current_world_vars=context.current_world_vars,
                )
                validation_result = validator.validate(response)

                # Log validacion
                self.validation_logger.log_validation(
                    response,
                    validation_result,
                    metadata={"attempt": attempt, "model": self.model}
                )

                # Si es valida, retornar
                if validation_result.is_valid:
                    return self._convert_to_proposal(response)

                # Si no es valida, reintentar con feedback
                if attempt < self.max_retries:
                    # Añadir feedback al prompt
                    feedback = self._build_validation_feedback(validation_result)
                    prompt = prompt + "\n\n" + feedback
                    continue
                else:
                    # Maximo intentos alcanzado
                    raise ValueError(
                        f"Respuesta invalida despues de {self.max_retries} intentos: "
                        f"{validation_result}"
                    )

            except anthropic.APIError as e:
                # Error de API, reintentar con backoff exponencial
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # 2, 4, 8 segundos
                    print(f"API error (attempt {attempt}/{self.max_retries}): {e}")
                    print(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.failed_calls += 1
                    raise

            except json.JSONDecodeError as e:
                # Error parseando JSON
                if attempt < self.max_retries:
                    print(f"JSON parse error (attempt {attempt}/{self.max_retries}): {e}")
                    print(f"Response was: {response_text[:200]}...")
                    continue
                else:
                    self.failed_calls += 1
                    raise ValueError(f"Failed to parse JSON after {self.max_retries} attempts: {e}")

            except Exception as e:
                # Otro error
                self.failed_calls += 1
                raise

        # No deberia llegar aqui
        self.failed_calls += 1
        raise RuntimeError("Unexpected error in generate_narrative")

    def _build_prompt(self, context: NarrativeContext) -> str:
        """Construye el prompt completo usando ContextBuilder."""
        # Obtener cadena de commits
        commit_chain = context.commit_chain if context.commit_chain else []

        return self.context_builder.build_context(
            world=context.world_definition,
            commit_chain=commit_chain,
            dramatic_state=context.current_dramatic_state,
            forced_constraint=context.forced_constraint,
            player_choice=context.player_choice,
        )

    async def _call_claude(self, prompt: str) -> str:
        """
        Llama a la API de Claude.

        Args:
            prompt: El prompt completo.

        Returns:
            str: La respuesta de Claude (texto JSON).
        """
        # System prompt
        system_prompt = self.context_builder.build_system_prompt()

        # Llamar a Claude
        message = await self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )

        # Actualizar stats
        self.total_tokens_used += message.usage.input_tokens + message.usage.output_tokens

        # Extraer texto de respuesta
        response_text = message.content[0].text

        return response_text

    def _parse_response(self, response_text: str) -> NarrativeResponse:
        """
        Parsea la respuesta JSON de Claude.

        Args:
            response_text: Texto de respuesta (debe ser JSON).

        Returns:
            NarrativeResponse parseada.

        Raises:
            json.JSONDecodeError: Si no es JSON valido.
            ValidationError: Si el schema de Pydantic falla.
        """
        # Claude a veces incluye markdown code blocks, removerlos
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]  # Remover ```json
        if text.startswith("```"):
            text = text[3:]  # Remover ```
        if text.endswith("```"):
            text = text[:-3]  # Remover ``` final
        text = text.strip()

        # Parsear JSON
        data = json.loads(text)

        # Validar con Pydantic
        response = NarrativeResponse(**data)

        return response

    def _build_validation_feedback(self, validation_result) -> str:
        """Construye feedback para la IA si la validacion fallo."""
        errors = validation_result.errors[:3]  # Top 3 errores
        error_text = "\n".join(f"- {e}" for e in errors)

        return f"""
========================================
RESPUESTA INVALIDA - CORRIGE LOS SIGUIENTES ERRORES
========================================

{error_text}

Por favor, genera una nueva respuesta JSON que corrija estos problemas.
Asegurate de:
1. Seguir el schema exacto especificado
2. Respetar todas las constraints del mundo
3. No incluir texto adicional fuera del JSON
"""

    def _convert_to_proposal(self, response: NarrativeResponse) -> NarrativeProposal:
        """Convierte NarrativeResponse a NarrativeProposal."""
        entity_deltas, world_deltas, dramatic_delta, choices = response.to_core_models()

        return NarrativeProposal(
            narrative_text=response.narrative,
            summary=response.summary,
            choices=choices,
            entity_deltas=entity_deltas,
            world_deltas=world_deltas,
            dramatic_delta=dramatic_delta,
            causal_reason=response.causal_reason,
            is_ending=response.is_ending,
            raw_response=response.model_dump(),
        )

    def get_stats(self) -> dict:
        """Retorna estadisticas del adapter."""
        success_rate = (
            (self.total_calls - self.failed_calls) / self.total_calls
            if self.total_calls > 0
            else 0
        )

        return {
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "success_rate": success_rate,
            "total_tokens_used": self.total_tokens_used,
            "avg_tokens_per_call": (
                self.total_tokens_used / self.total_calls
                if self.total_calls > 0
                else 0
            ),
            "model": self.model,
            "validation_stats": self.validation_logger.get_error_stats(),
        }

    def export_validation_log(self, filepath: str):
        """Exporta el log de validaciones a un archivo."""
        self.validation_logger.export_to_file(filepath)


class AnthropicConfig:
    """
    Helper para configuracion de Anthropic desde archivo o env vars.
    """

    @staticmethod
    def from_env() -> dict:
        """Carga configuracion desde variables de entorno."""
        return {
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048")),
            "temperature": float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
        }

    @staticmethod
    def from_file(filepath: str) -> dict:
        """Carga configuracion desde archivo JSON."""
        with open(filepath, "r") as f:
            return json.load(f)
