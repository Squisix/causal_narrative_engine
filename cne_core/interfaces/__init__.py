"""
cne_core/interfaces — Contratos públicos del motor

Estas son las interfaces que cualquier integrador externo debe implementar
para conectar el CNE a su stack de persistencia y IA.

El Core Engine SOLO conoce estas abstracciones, nunca implementaciones concretas.
Eso es lo que hace el motor independiente y reutilizable.
"""

from cne_core.interfaces.repository import NarrativeRepository
from cne_core.interfaces.ai_adapter import AIAdapter

__all__ = [
    "NarrativeRepository",
    "AIAdapter",
]
