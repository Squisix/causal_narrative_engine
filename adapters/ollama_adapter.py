"""
adapters/ollama_adapter.py - Implementacion con Ollama (LLMs locales)

Usa Ollama para generar narrativa con modelos locales gratuitos.

Requiere:
- Instalar Ollama: https://ollama.com
- Descargar un modelo: ollama pull gemma3:4b

Modelos recomendados (ligeros):
- gemma3:4b (~3GB RAM, buen balance calidad/velocidad)
- qwen3:4b (~3GB RAM, muy bueno siguiendo instrucciones)
- llama3.2:3b (~2GB RAM, intermedio)
- mistral:7b (~4GB RAM, requiere GPU o mucha RAM)
"""

import json
import asyncio

import httpx

from cne_core.interfaces.ai_adapter import (
    AIAdapter, NarrativeContext, NarrativeProposal, AIGenerationError
)
from cne_core.ai.response_schema import NarrativeResponse
from cne_core.ai.context_builder import ContextBuilder


class OllamaAdapter(AIAdapter):
    """
    AIAdapter que usa Ollama para generar narrativa con LLMs locales.

    Comunica con Ollama via su API HTTP (POST /api/chat).
    No requiere SDKs adicionales — solo httpx.
    """

    def __init__(
        self,
        model: str = "gemma3:4b",
        base_url: str = "http://localhost:11434",
        temperature: float = 0.7,
        max_retries: int = 2,
        timeout: float = 120.0,
    ):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout

        self.context_builder = ContextBuilder()

        self.total_calls = 0
        self.failed_calls = 0

    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal:
        self.total_calls += 1

        system_prompt = self.context_builder.build_system_prompt()
        user_prompt = self._build_prompt(context)

        for attempt in range(1, self.max_retries + 1):
            try:
                response_text = await self._call_ollama(system_prompt, user_prompt)
                response = self._parse_response(response_text)
                return self._convert_to_proposal(response)

            except (json.JSONDecodeError, ValueError) as e:
                if attempt < self.max_retries:
                    user_prompt = (
                        user_prompt
                        + f"\n\nTu respuesta anterior fue invalida: {e}\n"
                        + "Genera SOLO JSON valido con el schema especificado. "
                        + "No incluyas texto fuera del JSON."
                    )
                    continue
                self.failed_calls += 1
                raise AIGenerationError(
                    f"Ollama retorno respuesta invalida despues de {self.max_retries} intentos: {e}"
                )

            except httpx.HTTPError as e:
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                self.failed_calls += 1
                raise AIGenerationError(f"Error conectando con Ollama: {e}")

            except Exception as e:
                self.failed_calls += 1
                raise AIGenerationError(f"Error inesperado: {e}")

        self.failed_calls += 1
        raise AIGenerationError("Error inesperado en generate_narrative")

    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        response = self._parse_response(raw_response)
        return self._convert_to_proposal(response)

    def get_model_info(self) -> dict[str, str]:
        return {
            "provider": "Ollama",
            "model": self.model,
            "version": "local",
        }

    def _build_prompt(self, context: NarrativeContext) -> str:
        return self.context_builder.build_context(
            world=context.world_definition,
            commit_chain=context.commit_chain or [],
            dramatic_state=context.current_dramatic_state,
            forced_constraint=context.forced_constraint,
            player_choice=context.player_choice,
        )

    async def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
            "options": {
                "temperature": self.temperature,
            },
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            resp.raise_for_status()

        data = resp.json()
        return data["message"]["content"]

    def _parse_response(self, response_text: str) -> NarrativeResponse:
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        data = json.loads(text)
        data = self._normalize_response(data)
        return NarrativeResponse(**data)

    def _normalize_response(self, data: dict) -> dict:
        """Normaliza respuestas de modelos pequenos que no siguen el schema exacto."""
        # choices: si el modelo retorno dicts en vez de strings, extraer el texto
        if "choices" in data and data["choices"]:
            normalized_choices = []
            normalized_previews = []
            for item in data["choices"]:
                if isinstance(item, dict):
                    choice_text = item.get("choice") or item.get("text") or str(item)
                    normalized_choices.append(choice_text)
                    normalized_previews.append({
                        "choice": choice_text,
                        "tension_delta": item.get("tension_delta", 0),
                        "hope_delta": item.get("hope_delta", 0),
                        "chaos_delta": item.get("chaos_delta", 0),
                        "tone": item.get("tone", "neutral"),
                    })
                else:
                    normalized_choices.append(str(item))
            data["choices"] = normalized_choices
            if normalized_previews and not data.get("choice_dramatic_preview"):
                data["choice_dramatic_preview"] = normalized_previews

        # summary: truncar si es muy largo
        if "summary" in data and isinstance(data["summary"], str) and len(data["summary"]) > 200:
            data["summary"] = data["summary"][:197] + "..."

        # narrative: aceptar "narrative_text" como alias
        if "narrative" not in data and "narrative_text" in data:
            data["narrative"] = data.pop("narrative_text")

        # choice_dramatic_preview: limpiar entradas invalidas
        if "choice_dramatic_preview" in data:
            valid_previews = []
            for p in data["choice_dramatic_preview"]:
                if isinstance(p, dict) and "choice" in p:
                    valid_previews.append(p)
            data["choice_dramatic_preview"] = valid_previews

        # entity_deltas: debe ser lista de dicts con campos correctos
        if "entity_deltas" in data:
            if not isinstance(data["entity_deltas"], list):
                data["entity_deltas"] = []
            else:
                normalized_ed = []
                for ed in data["entity_deltas"]:
                    if not isinstance(ed, dict):
                        continue
                    ed.setdefault("entity_name", ed.get("entity_id", "unknown"))
                    ed.setdefault("entity_id", ed.get("entity_name", "unknown"))
                    ed.setdefault("attribute", ed.get("entity_delta", "state"))
                    ed.setdefault("new_value", ed.get("old_value", 0))
                    ed.setdefault("old_value", ed.get("new_value", 0))
                    normalized_ed.append(ed)
                data["entity_deltas"] = normalized_ed

        # world_deltas: debe ser lista de dicts con campos correctos
        if "world_deltas" in data:
            if not isinstance(data["world_deltas"], list):
                data["world_deltas"] = []
            else:
                normalized_wd = []
                for wd in data["world_deltas"]:
                    if not isinstance(wd, dict):
                        continue
                    wd.setdefault("variable", wd.get("name", "world_state"))
                    wd.setdefault("new_value", wd.get("old_value", 0))
                    wd.setdefault("old_value", wd.get("new_value", 0))
                    normalized_wd.append(wd)
                data["world_deltas"] = normalized_wd

        # dramatic_deltas: asegurar que existe con defaults
        if "dramatic_deltas" not in data:
            data["dramatic_deltas"] = {
                "tension": 0, "hope": 0, "chaos": 0, "rhythm": 0,
                "saturation": 0, "connection": 0, "mystery": 0,
            }

        # causal_reason: default si no existe o es muy corto
        if not data.get("causal_reason") or len(str(data["causal_reason"])) < 10:
            data["causal_reason"] = "Evento generado por la narrativa del mundo."

        # is_ending: default false
        if "is_ending" not in data:
            data["is_ending"] = False

        return data

    def _convert_to_proposal(self, response: NarrativeResponse) -> NarrativeProposal:
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
        success_rate = (
            (self.total_calls - self.failed_calls) / self.total_calls
            if self.total_calls > 0
            else 0
        )
        return {
            "total_calls": self.total_calls,
            "failed_calls": self.failed_calls,
            "success_rate": success_rate,
            "model": self.model,
            "base_url": self.base_url,
        }
