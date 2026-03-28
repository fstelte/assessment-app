"""Simple Redis-backed cache helpers."""
from __future__ import annotations

import functools
import json
import logging
from typing import Any, Callable

from flask import current_app

logger = logging.getLogger(__name__)


def _redis():
    from ..extensions import get_redis
    return get_redis()


def cache_json(key: str, ttl: int = 60):
    """Decorator: cache the return value of a function as JSON in Redis.

    Falls back to calling the function directly if Redis is unavailable.
    Only caches calls with no arguments (suitable for lookup/aggregate functions).
    """
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs) -> Any:
            if not current_app.config.get("REDIS_URL"):
                return fn(*args, **kwargs)
            try:
                r = _redis()
                cached = r.get(key)
                if cached is not None:
                    return json.loads(cached)
                result = fn(*args, **kwargs)
                r.setex(key, ttl, json.dumps(result))
                return result
            except Exception:
                logger.warning("Redis cache miss (error); calling function directly", exc_info=True)
                return fn(*args, **kwargs)

        def invalidate() -> None:
            try:
                _redis().delete(key)
            except Exception:
                logger.warning("Redis cache invalidation failed", exc_info=True)

        wrapper.invalidate = invalidate  # type: ignore[attr-defined]
        return wrapper
    return decorator
