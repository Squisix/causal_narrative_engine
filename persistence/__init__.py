"""
persistence — Persistence layer for the CNE

Concrete implementations of NarrativeRepository using SQLAlchemy 2.0 async.

Structure:
- models/       ORM models (map dataclasses → SQL tables)
- repositories/ NarrativeRepository implementations
- queries/      Complex queries (recursive CTE, topological order)
"""
