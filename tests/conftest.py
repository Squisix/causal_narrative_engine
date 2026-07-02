"""
tests/conftest.py — Shared fixtures for all tests.

Ensures async tests share a session-scoped event loop so asyncpg
pool connections remain valid across tests.
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_engine_cache():
    """Clear the narrative service engine cache between tests."""
    yield
    try:
        from api.services.narrative_service_v2 import _engine_cache
        _engine_cache.clear()
    except ImportError:
        pass


@pytest.fixture(scope="session", autouse=True)
async def _dispose_db_engine():
    """Dispose the global database engine at the end of the test session."""
    yield
    try:
        import persistence.database as db_module
        if db_module._global_engine is not None:
            await db_module._global_engine.dispose()
            db_module._global_engine = None
            db_module._global_session_maker = None
    except ImportError:
        pass
