"""
persistence/cache.py — Cache layer with Redis (optional)

Provides RedisCache and NullCache with the same interface.
If REDIS_URL is not configured, NullCache (no-op) is used.
If Redis goes down, operations fail silently.
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime
from enum import Enum
from typing import Any

from cne_core.models.commit import NarrativeCommit, NarrativeChoice
from cne_core.models.world import WorldDefinition, Entity, EntityType, NarrativeTone

logger = logging.getLogger(__name__)


# ── Serialization helpers ────────────────────────────────────────────────────


def _serialize(obj: Any) -> str:
    """Serializes dataclasses, datetimes, and enums to a JSON string."""

    def _default(o: Any) -> Any:
        if isinstance(o, datetime):
            return {"__datetime__": o.isoformat()}
        if isinstance(o, Enum):
            return o.value
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    if hasattr(obj, "__dataclass_fields__"):
        data = asdict(obj)
    elif isinstance(obj, list):
        data = [asdict(item) if hasattr(item, "__dataclass_fields__") else item for item in obj]
    else:
        data = obj

    return json.dumps(data, default=_default, ensure_ascii=False)


def _restore_datetime(d: dict) -> dict:
    """Recursively restore __datetime__ markers back to datetime objects."""
    for key, value in d.items():
        if isinstance(value, dict):
            if "__datetime__" in value:
                d[key] = datetime.fromisoformat(value["__datetime__"])
            else:
                _restore_datetime(value)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    if "__datetime__" in item:
                        value[i] = datetime.fromisoformat(item["__datetime__"])
                    else:
                        _restore_datetime(item)
    return d


def _deserialize_commits(data: str) -> list[NarrativeCommit]:
    """Deserializes a list of NarrativeCommit from JSON."""
    items = json.loads(data)
    commits = []
    for d in items:
        d = _restore_datetime(d)
        commits.append(NarrativeCommit(**d))
    return commits


def _deserialize_choices(data: str) -> list[NarrativeChoice]:
    """Deserializes a list of NarrativeChoice from JSON."""
    items = json.loads(data)
    return [NarrativeChoice(**d) for d in items]


def _deserialize_world(data: str) -> WorldDefinition:
    """Deserializes a WorldDefinition from JSON."""
    d = json.loads(data)
    d = _restore_datetime(d)

    if "tone" in d and isinstance(d["tone"], str):
        d["tone"] = NarrativeTone(d["tone"])

    if "initial_entities" in d:
        entities = []
        for e in d["initial_entities"]:
            if "entity_type" in e and isinstance(e["entity_type"], str):
                e["entity_type"] = EntityType(e["entity_type"])
            entities.append(Entity(**e))
        d["initial_entities"] = entities

    return WorldDefinition(**d)


# ── Cache interface ──────────────────────────────────────────────────────────


class CacheBackend(ABC):
    """Abstract interface for cache. RedisCache and NullCache implement it."""

    @abstractmethod
    async def get(self, key: str) -> str | None:
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> None:
        pass

    @abstractmethod
    async def close(self) -> None:
        pass

    # ── High-level methods ────────────────────────────────────────────────

    async def get_trunk(self, commit_id: str) -> list[NarrativeCommit] | None:
        try:
            data = await self.get(f"trunk:{commit_id}")
            if data:
                return _deserialize_commits(data)
        except Exception as e:
            logger.warning("Cache get_trunk failed: %s", e)
        return None

    async def set_trunk(
        self, commit_id: str, commits: list[NarrativeCommit], ttl: int = 3600
    ) -> None:
        try:
            await self.set(f"trunk:{commit_id}", _serialize(commits), ttl)
        except Exception as e:
            logger.warning("Cache set_trunk failed: %s", e)

    async def get_world(self, world_id: str) -> WorldDefinition | None:
        try:
            data = await self.get(f"world:{world_id}")
            if data:
                return _deserialize_world(data)
        except Exception as e:
            logger.warning("Cache get_world failed: %s", e)
        return None

    async def set_world(
        self, world_id: str, world: WorldDefinition, ttl: int = 1800
    ) -> None:
        try:
            await self.set(f"world:{world_id}", _serialize(world), ttl)
        except Exception as e:
            logger.warning("Cache set_world failed: %s", e)

    async def get_choices(self, commit_id: str) -> list[NarrativeChoice] | None:
        try:
            data = await self.get(f"choices:{commit_id}")
            if data:
                return _deserialize_choices(data)
        except Exception as e:
            logger.warning("Cache get_choices failed: %s", e)
        return None

    async def set_choices(
        self, commit_id: str, choices: list[NarrativeChoice], ttl: int = 3600
    ) -> None:
        try:
            await self.set(f"choices:{commit_id}", _serialize(choices), ttl)
        except Exception as e:
            logger.warning("Cache set_choices failed: %s", e)

    async def invalidate_world(self, world_id: str) -> None:
        try:
            await self.delete(f"world:{world_id}")
        except Exception as e:
            logger.warning("Cache invalidate_world failed: %s", e)


# ── Redis implementation ─────────────────────────────────────────────────────


class RedisCache(CacheBackend):
    """Cache backed by Redis using redis.asyncio."""

    def __init__(self, client: Any):
        self._client = client

    async def get(self, key: str) -> str | None:
        value = await self._client.get(key)
        if value is not None:
            return value.decode("utf-8") if isinstance(value, bytes) else value
        return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        if ttl:
            await self._client.set(key, value, ex=ttl)
        else:
            await self._client.set(key, value)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        async for key in self._client.scan_iter(match=pattern):
            await self._client.delete(key)

    async def close(self) -> None:
        await self._client.aclose()


# ── Null implementation (no-op) ──────────────────────────────────────────────


class NullCache(CacheBackend):
    """No-op cache for when Redis is not configured."""

    async def get(self, key: str) -> str | None:
        return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        pass

    async def delete(self, key: str) -> None:
        pass

    async def delete_pattern(self, pattern: str) -> None:
        pass

    async def close(self) -> None:
        pass


# ── Factory ──────────────────────────────────────────────────────────────────


async def create_cache(redis_url: str | None = None) -> CacheBackend:
    """
    Creates the appropriate cache backend.

    If redis_url is None or the connection fails, returns NullCache.
    """
    if not redis_url:
        logger.info("No REDIS_URL configured — using NullCache (no caching)")
        return NullCache()

    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(
            redis_url,
            decode_responses=False,
            max_connections=10,
        )
        await client.ping()
        logger.info("Redis connected at %s", redis_url)
        return RedisCache(client)
    except ImportError:
        logger.warning("redis package not installed — using NullCache")
        return NullCache()
    except Exception as e:
        logger.warning("Redis connection failed (%s) — using NullCache", e)
        return NullCache()
