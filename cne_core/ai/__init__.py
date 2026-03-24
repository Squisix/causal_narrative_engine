"""
cne_core/ai/ - AI integration layer

Este paquete contiene todo lo relacionado con la generación de narrativa con IA.
Es independiente del proveedor específico (Anthropic, OpenAI, etc.)
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
