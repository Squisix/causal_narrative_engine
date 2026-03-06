"""
persistence — Capa de persistencia para el CNE

Implementaciones concretas de NarrativeRepository usando SQLAlchemy 2.0 async.

Estructura:
- models/       ORM models (mapean dataclasses → tablas SQL)
- repositories/ Implementaciones de NarrativeRepository
- queries/      Queries complejas (CTE recursiva, topological order)
- state_rebuilder.py  Reconstrucción de estado desde deltas
"""
