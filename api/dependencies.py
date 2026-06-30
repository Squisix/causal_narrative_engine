"""
api/dependencies.py - Dependency Injection

Provee dependencias para FastAPI (Repository, AI Adapters, etc.)
"""

from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from persistence.database import get_session
from persistence.repositories.postgresql_repository import PostgreSQLRepository
from cne_core.interfaces.repository import NarrativeRepository
from adapters.mock_adapter import MockAdapter
from api.config import get_settings
from api.services.narrative_service_v2 import NarrativeServiceV2

try:
    from adapters.anthropic_adapter import AnthropicAdapter
    ANTHROPIC_AVAILABLE = True
except ImportError:
    AnthropicAdapter = None
    ANTHROPIC_AVAILABLE = False

try:
    from adapters.ollama_adapter import OllamaAdapter
    OLLAMA_AVAILABLE = True
except ImportError:
    OllamaAdapter = None
    OLLAMA_AVAILABLE = False


# ── Repository ──────────────────────────────────────────────────────────────


async def get_repository() -> AsyncGenerator[NarrativeRepository, None]:
    """
    Dependency para obtener el Repository.

    Crea una sesión de DB y la cierra automáticamente al terminar la request.
    """
    async for session in get_session():
        repo = PostgreSQLRepository(session)
        yield repo


# ── AI Adapters ─────────────────────────────────────────────────────────────


_mock_adapter_instance = None


def get_mock_adapter() -> MockAdapter:
    """
    Retorna una instancia singleton del MockAdapter.

    Útil para testing y desarrollo sin API keys.
    """
    global _mock_adapter_instance
    if _mock_adapter_instance is None:
        _mock_adapter_instance = MockAdapter(deterministic=True, seed=42)
    return _mock_adapter_instance


_anthropic_adapter_instance = None


def get_anthropic_adapter() -> AnthropicAdapter:
    """
    Retorna una instancia singleton del AnthropicAdapter.

    Usa la configuración de settings (API key, modelo, etc.)
    """
    if not ANTHROPIC_AVAILABLE:
        raise ValueError("Anthropic adapter not available. Install: pip install anthropic")

    global _anthropic_adapter_instance
    if _anthropic_adapter_instance is None:
        settings = get_settings()

        if not settings.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not configured. "
                "Set it in .env or pass adapter_config with api_key"
            )

        _anthropic_adapter_instance = AnthropicAdapter(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            temperature=settings.anthropic_temperature,
        )

    return _anthropic_adapter_instance


_ollama_adapter_instance = None


def get_ollama_adapter() -> OllamaAdapter:
    """Retorna una instancia singleton del OllamaAdapter."""
    if not OLLAMA_AVAILABLE:
        raise ValueError("Ollama adapter not available. Install: pip install httpx")

    global _ollama_adapter_instance
    if _ollama_adapter_instance is None:
        settings = get_settings()
        _ollama_adapter_instance = OllamaAdapter(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=settings.ollama_temperature,
        )

    return _ollama_adapter_instance


def get_ai_adapter(adapter_type: str = "mock", adapter_config: dict = None):
    """
    Factory para obtener un AI adapter.

    Args:
        adapter_type: "mock", "anthropic", o "ollama"
        adapter_config: Configuracion especifica (opcional)

    Returns:
        AIAdapter instancia
    """
    if adapter_type == "mock":
        return get_mock_adapter()

    elif adapter_type == "anthropic":
        if adapter_config and "api_key" in adapter_config:
            if not ANTHROPIC_AVAILABLE:
                raise ValueError("Anthropic not available. Install: pip install anthropic")

            return AnthropicAdapter(
                api_key=adapter_config["api_key"],
                model=adapter_config.get("model", "claude-3-5-sonnet-20241022"),
                temperature=adapter_config.get("temperature", 0.7),
            )

        return get_anthropic_adapter()

    elif adapter_type == "ollama":
        if adapter_config:
            if not OLLAMA_AVAILABLE:
                raise ValueError("Ollama adapter not available. Install: pip install httpx")
            return OllamaAdapter(
                model=adapter_config.get("model", "gemma3:4b"),
                base_url=adapter_config.get("base_url", "http://localhost:11434"),
                temperature=adapter_config.get("temperature", 0.7),
            )

        return get_ollama_adapter()

    else:
        raise ValueError(f"Unknown adapter type: {adapter_type}. Valid: mock, anthropic, ollama")


# ── Narrative Service V2 ────────────────────────────────────────────────────


async def get_narrative_service_v2(
    repo: NarrativeRepository = Depends(get_repository)
) -> NarrativeServiceV2:
    """
    Dependency para obtener el NarrativeServiceV2.

    Usa el Repository inyectado (PostgreSQL).
    """
    return NarrativeServiceV2(repository=repo)
