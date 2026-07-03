"""
adapters/ - AIAdapter implementations

This package contains concrete implementations of the AIAdapter interface
for different AI providers.

Available implementations:
- MockAdapter: For tests without API key
- AnthropicAdapter: Claude (Anthropic)
- OpenAIAdapter: GPT (OpenAI) - optional
"""

from adapters.mock_adapter import MockAdapter

__all__ = ["MockAdapter"]

# AnthropicAdapter is imported only if anthropic is installed
try:
    from adapters.anthropic_adapter import AnthropicAdapter
    __all__.append("AnthropicAdapter")
except ImportError:
    pass

# OllamaAdapter is imported only if httpx is installed
try:
    from adapters.ollama_adapter import OllamaAdapter
    __all__.append("OllamaAdapter")
except ImportError:
    pass

# OpenAIAdapter is imported only if openai is installed
try:
    from adapters.openai_adapter import OpenAIAdapter
    __all__.append("OpenAIAdapter")
except ImportError:
    pass
