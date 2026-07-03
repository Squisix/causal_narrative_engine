"""
cne_core/ai/ - AI integration layer

This package contains everything related to AI-powered narrative generation.
It is independent of the specific provider (Anthropic, OpenAI, etc.)
"""

from cne_core.ai.response_schema import (
    NarrativeResponse,
    ChoicePreview,
    DramaticDeltaDict,
)
from cne_core.ai.context_builder import ContextBuilder
from cne_core.ai.response_validator import ResponseValidator

__all__ = [
    "NarrativeResponse",
    "ChoicePreview",
    "DramaticDeltaDict",
    "ContextBuilder",
    "ResponseValidator",
]
