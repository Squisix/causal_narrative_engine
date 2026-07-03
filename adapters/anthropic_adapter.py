"""
adapters/anthropic_adapter.py - Implementation with Anthropic API (Claude)

This adapter uses Claude (Anthropic) to generate real narrative.

Requirements:
- pip install anthropic
- API key: ANTHROPIC_API_KEY in environment variable or config

Recommended models:
- claude-3-5-sonnet-20241022 (best quality/price balance)
- claude-opus-4 (highest quality, more expensive)
- claude-haiku-3 (fast and economical, for prototypes)
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
        "The 'anthropic' package is not installed.\n"
        "Install with: pip install anthropic"
    )

from cne_core.interfaces.ai_adapter import AIAdapter, NarrativeContext, NarrativeProposal
from cne_core.ai.response_schema import NarrativeResponse
from cne_core.ai.context_builder import ContextBuilder
from cne_core.ai.response_validator import ResponseValidator


class AnthropicAdapter(AIAdapter):
    """
    AIAdapter that uses Claude (Anthropic) to generate narrative.

    Handles:
    - Optimized prompt construction
    - Anthropic API calls
    - Retry logic with exponential backoff
    - Response validation
    - Error logging
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
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Claude model to use.
            max_tokens: Maximum tokens to generate.
            temperature: Temperature for generation (0.0-1.0).
            max_retries: Maximum attempts on API error.
            timeout: Timeout in seconds for API calls.
        """
        # API key
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key not found. Provide api_key or set ANTHROPIC_API_KEY env var."
            )

        # Async client
        self.client = AsyncAnthropic(api_key=self.api_key, timeout=timeout)

        # Configuration
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.max_retries = max_retries

        # Components
        self.context_builder = ContextBuilder()

        # Stats
        self.total_calls = 0
        self.total_tokens_used = 0
        self.failed_calls = 0

    async def generate_narrative(self, context: NarrativeContext) -> NarrativeProposal:
        """
        Generates narrative using Claude.

        Args:
            context: Narrative context with all necessary information.

        Returns:
            NarrativeProposal with the generated narrative.

        Raises:
            Exception: If it fails after max_retries attempts.
        """
        self.total_calls += 1

        # 1. Build the complete prompt
        prompt = self._build_prompt(context)

        # 2. Call Claude with retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                response_text = await self._call_claude(prompt)

                # 3. Parse JSON response
                response = self._parse_response(response_text)

                # 4. Validate response
                validator = ResponseValidator(
                    world=context.world_definition,
                    current_entities=context.current_entity_states,
                    current_world_vars=context.current_world_vars,
                )
                validation_result = validator.validate(response)

                # If valid, return
                if validation_result.is_valid:
                    return self._convert_to_proposal(response)

                # If not valid, retry with feedback
                if attempt < self.max_retries:
                    # Add feedback to prompt
                    feedback = self._build_validation_feedback(validation_result)
                    prompt = prompt + "\n\n" + feedback
                    continue
                else:
                    # Maximum attempts reached
                    raise ValueError(
                        f"Invalid response after {self.max_retries} attempts: "
                        f"{validation_result}"
                    )

            except anthropic.APIError as e:
                # API error, retry with exponential backoff
                if attempt < self.max_retries:
                    wait_time = 2 ** attempt  # 2, 4, 8 seconds
                    print(f"API error (attempt {attempt}/{self.max_retries}): {e}")
                    print(f"Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    self.failed_calls += 1
                    raise

            except json.JSONDecodeError as e:
                # JSON parsing error
                if attempt < self.max_retries:
                    print(f"JSON parse error (attempt {attempt}/{self.max_retries}): {e}")
                    print(f"Response was: {response_text[:200]}...")
                    continue
                else:
                    self.failed_calls += 1
                    raise ValueError(f"Failed to parse JSON after {self.max_retries} attempts: {e}")

            except Exception as e:
                # Other error
                self.failed_calls += 1
                raise

        # Should not reach here
        self.failed_calls += 1
        raise RuntimeError("Unexpected error in generate_narrative")

    def _build_prompt(self, context: NarrativeContext) -> str:
        """Builds the complete prompt using ContextBuilder."""
        # Get commit chain
        commit_chain = context.commit_chain if context.commit_chain else []

        return self.context_builder.build_context(
            world=context.world_definition,
            commit_chain=commit_chain,
            dramatic_state=context.current_dramatic_state,
            forced_constraint=context.forced_constraint,
            player_choice=context.player_choice,
            current_entity_states=context.current_entity_states or None,
            current_world_vars=context.current_world_vars or None,
        )

    async def _call_claude(self, prompt: str) -> str:
        """
        Calls the Claude API.

        Args:
            prompt: The complete prompt.

        Returns:
            str: Claude's response (JSON text).
        """
        # System prompt
        system_prompt = self.context_builder.build_system_prompt()

        # Call Claude
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

        # Update stats
        self.total_tokens_used += message.usage.input_tokens + message.usage.output_tokens

        # Extract response text
        response_text = message.content[0].text

        return response_text

    def _parse_response(self, response_text: str) -> NarrativeResponse:
        """
        Parses the JSON response from Claude.

        Args:
            response_text: Response text (must be JSON).

        Returns:
            Parsed NarrativeResponse.

        Raises:
            json.JSONDecodeError: If not valid JSON.
            ValidationError: If Pydantic schema fails.
        """
        # Claude sometimes includes markdown code blocks, remove them
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]  # Remove ```json
        if text.startswith("```"):
            text = text[3:]  # Remove ```
        if text.endswith("```"):
            text = text[:-3]  # Remove trailing ```
        text = text.strip()

        # Parse JSON
        data = json.loads(text)

        # Validate with Pydantic
        response = NarrativeResponse(**data)

        return response

    def _build_validation_feedback(self, validation_result) -> str:
        """Builds feedback for the AI if validation failed."""
        errors = validation_result.errors[:3]  # Top 3 errors
        error_text = "\n".join(f"- {e}" for e in errors)

        return f"""
========================================
INVALID RESPONSE - FIX THE FOLLOWING ERRORS
========================================

{error_text}

Please generate a new JSON response that fixes these issues.
Make sure to:
1. Follow the exact specified schema
2. Respect all world constraints
3. Do not include additional text outside the JSON
"""

    def _convert_to_proposal(self, response: NarrativeResponse) -> NarrativeProposal:
        """Converts NarrativeResponse to NarrativeProposal."""
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

    async def validate_response(self, raw_response: str) -> NarrativeProposal:
        """Parses and validates a raw Claude response."""
        validator = ResponseValidator()
        response = validator.parse_and_validate(raw_response)
        return self._convert_to_proposal(response)

    def get_model_info(self) -> dict[str, str]:
        """Returns model information."""
        return {
            "provider": "Anthropic",
            "model": self.model,
            "max_tokens": str(self.max_tokens),
        }

    def get_stats(self) -> dict:
        """Returns adapter statistics."""
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
        }


class AnthropicConfig:
    """
    Helper for Anthropic configuration from file or env vars.
    """

    @staticmethod
    def from_env() -> dict:
        """Loads configuration from environment variables."""
        return {
            "api_key": os.getenv("ANTHROPIC_API_KEY"),
            "model": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
            "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "2048")),
            "temperature": float(os.getenv("ANTHROPIC_TEMPERATURE", "0.7")),
        }

    @staticmethod
    def from_file(filepath: str) -> dict:
        """Loads configuration from JSON file."""
        with open(filepath, "r") as f:
            return json.load(f)
