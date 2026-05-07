"""
src/cache.py
Redis cache client with JSON serialisation.
Falls back silently to None on every call if Redis is unavailable —
callers must handle None by falling through to the DB.
"""
import os
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        import redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        _client.ping()
    except Exception as e:
        logger.warning(f"Redis unavailable — caching disabled: {e}")
        _client = None
    return _client


def cache_get(key: str) -> Optional[Any]:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        return json.loads(raw) if raw is not None else None
    except Exception:
        return None


def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception:
        pass


def cache_delete(key: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception:
        pass


def cache_delete_pattern(pattern: str) -> None:
    """Delete all keys matching a pattern (e.g. 'ubid:KA-UBID-*')."""
    client = _get_client()
    if client is None:
        return
    try:
        keys = client.keys(pattern)
        if keys:
            client.delete(*keys)
    except Exception:
        pass
