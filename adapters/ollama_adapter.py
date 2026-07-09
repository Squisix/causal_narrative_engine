"""
adapters/ollama_adapter.py - Implementation with Ollama (local LLMs)

Uses Ollama to generate narrative with free local models.

Requirements:
- Install Ollama: https://ollama.com
- Download a model: ollama pull gemma3:4b

Recommended models (lightweight):
- gemma3:4b (~3GB RAM, good quality/speed balance)
- qwen3:4b (~3GB RAM, very good at following instructions)
- llama3.2:3b (~2GB RAM, intermediate)
- mistral:7b (~4GB RAM, requires GPU or lots of RAM)
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
    AIAdapter that uses Ollama to generate narrative with local LLMs.

    Communicates with Ollama via its HTTP API (POST /api/chat).
    Does not require additional SDKs -- only httpx.
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
        world_id = context.world_definition.id if hasattr(context.world_definition, "id") else "unknown"

        for attempt in range(1, self.max_retries + 1):
            try:
                response_text = await self._call_ollama(system_prompt, user_prompt)
                response = self._parse_response(response_text)
                proposal = self._convert_to_proposal(response)

                # Log successful interaction
                from adapters.logging_utils import log_ai_interaction
                log_ai_interaction(
                    world_id=world_id,
                    adapter_name=f"ollama_{self.model}",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    raw_response=response_text,
                    success=True,
                )
                return proposal

            except (json.JSONDecodeError, ValueError) as e:
                # Log failed attempt
                from adapters.logging_utils import log_ai_interaction
                log_ai_interaction(
                    world_id=world_id,
                    adapter_name=f"ollama_{self.model}",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    raw_response=response_text if 'response_text' in locals() else None,
                    success=False,
                    error_msg=f"Attempt {attempt} failed: {e}",
                )
                if attempt < self.max_retries:
                    user_prompt = (
                        user_prompt
                        + f"\n\nYour previous response was invalid: {e}\n"
                        + "Generate ONLY valid JSON with the specified schema. "
                        + "Do not include text outside the JSON."
                    )
                    continue
                self.failed_calls += 1
                raise AIGenerationError(
                    f"Ollama returned invalid response after {self.max_retries} attempts: {e}"
                )

            except httpx.HTTPError as e:
                # Log HTTP connection failure
                from adapters.logging_utils import log_ai_interaction
                log_ai_interaction(
                    world_id=world_id,
                    adapter_name=f"ollama_{self.model}",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    raw_response=None,
                    success=False,
                    error_msg=f"HTTP Connection Error on attempt {attempt}: {e}",
                )
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                self.failed_calls += 1
                raise AIGenerationError(f"Error connecting to Ollama: {e}")

            except Exception as e:
                # Log unexpected failure
                from adapters.logging_utils import log_ai_interaction
                log_ai_interaction(
                    world_id=world_id,
                    adapter_name=f"ollama_{self.model}",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    raw_response=None,
                    success=False,
                    error_msg=f"Unexpected error: {e}",
                )
                self.failed_calls += 1
                raise AIGenerationError(f"Unexpected error: {e}")

        self.failed_calls += 1
        raise AIGenerationError("Unexpected error in generate_narrative")

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
            player_choice_tone=context.player_choice_tone,
            current_entity_states=context.current_entity_states or None,
            current_world_vars=context.current_world_vars or None,
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
        """Normalizes responses from small models that don't follow the exact schema."""
        # choices: if the model returned dicts instead of strings, extract the text
        if "choices" in data and data["choices"]:
            normalized_choices = []
            normalized_tones = []
            for item in data["choices"]:
                if isinstance(item, dict):
                    choice_text = item.get("choice") or item.get("text") or str(item)
                    normalized_choices.append(choice_text)
                    normalized_tones.append(item.get("tone", "neutral"))
                else:
                    normalized_choices.append(str(item))
            data["choices"] = normalized_choices
            if normalized_tones and not data.get("choice_tones"):
                data["choice_tones"] = normalized_tones

        # summary: truncate if too long
        if "summary" in data and isinstance(data["summary"], str) and len(data["summary"]) > 200:
            data["summary"] = data["summary"][:197] + "..."

        # narrative: accept "narrative_text" as alias
        if "narrative" not in data and "narrative_text" in data:
            data["narrative"] = data.pop("narrative_text")

        # choice_tones: ensure it's a list of strings
        if "choice_tones" in data:
            data["choice_tones"] = [str(t) for t in data["choice_tones"] if t]

        # Backward compat: strip old choice_dramatic_preview if present
        data.pop("choice_dramatic_preview", None)

        # entity_deltas: must be a list of dicts with correct fields
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

        # world_deltas: must be a list of dicts with correct fields
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

        # entity_creations: must be a list of dicts with correct fields
        if "entity_creations" in data:
            if not isinstance(data["entity_creations"], list):
                data["entity_creations"] = []
            else:
                normalized_ec = []
                for ec in data["entity_creations"]:
                    if not isinstance(ec, dict):
                        continue
                    ec.setdefault("entity_name", "Unknown Entity")
                    ec.setdefault("entity_type", "character")
                    ec.setdefault("attributes", {})
                    normalized_ec.append(ec)
                data["entity_creations"] = normalized_ec

        # dramatic_deltas: ensure it exists with defaults
        if "dramatic_deltas" not in data:
            data["dramatic_deltas"] = {
                "tension": 0, "hope": 0, "chaos": 0, "rhythm": 0,
                "saturation": 0, "connection": 0, "mystery": 0,
            }

        # causal_reason: default if missing or too short
        if not data.get("causal_reason") or len(str(data["causal_reason"])) < 10:
            data["causal_reason"] = "Event generated by the world's narrative."

        # is_ending: default false
        if "is_ending" not in data:
            data["is_ending"] = False

        return data

    def _convert_to_proposal(self, response: NarrativeResponse) -> NarrativeProposal:
        entity_deltas, entity_creations, world_deltas, dramatic_delta, choices = response.to_core_models()

        return NarrativeProposal(
            narrative_text=response.narrative,
            summary=response.summary,
            choices=choices,
            entity_deltas=entity_deltas,
            entity_creations=entity_creations,
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
