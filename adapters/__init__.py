"""
adapters/ - Implementaciones de AIAdapter

Este paquete contiene implementaciones concretas de la interfaz AIAdapter
para diferentes proveedores de IA.

Implementaciones disponibles:
- MockAdapter: Para tests sin API key
- AnthropicAdapter: Claude (Anthropic)
- OpenAIAdapter: GPT (OpenAI) - opcional
"""

from adapters.mock_adapter import MockAdapter

__all__ = ["MockAdapter"]

# AnthropicAdapter se importa solo si anthropic esta instalado
try:
    from adapters.anthropic_adapter import AnthropicAdapter
    __all__.append("AnthropicAdapter")
except ImportError:
    pass

# OpenAIAdapter se importa solo si openai esta instalado
try:
    from adapters.openai_adapter import OpenAIAdapter
    __all__.append("OpenAIAdapter")
except ImportError:
    pass
