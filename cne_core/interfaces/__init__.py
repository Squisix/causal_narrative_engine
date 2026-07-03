"""
cne_core/interfaces — Public contracts of the engine

These are the interfaces that any external integrator must implement
to connect the CNE to their persistence and AI stack.

The Core Engine ONLY knows these abstractions, never concrete implementations.
This is what makes the engine standalone and reusable.
"""

from cne_core.interfaces.repository import NarrativeRepository
from cne_core.interfaces.ai_adapter import AIAdapter

__all__ = [
    "NarrativeRepository",
    "AIAdapter",
]
