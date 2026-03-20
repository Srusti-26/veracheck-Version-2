"""
Redis Cache Service — async Redis wrapper with graceful degradation.

Falls back to in-memory dict if Redis is unavailable.
"""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("cache")


class RedisCache:
    """
    Async Redis cache with in-memory fallback.
    Used for:
    - Caching fact-check results (key: claim hash, TTL: 1hr)
    - Storing batch job results (key: job:{id}, TTL: 5min)
    """

    def __init__(self, redis_url: str):
        self._url = redis_url
        self._client = None
        self._fallback: Dict[str, Any] = {}
        self._hit_count = 0
        self._miss_count = 0

    async def connect(self):
        try:
            import redis.asyncio as aioredis
            self._client = aioredis.from_url(self._url, decode_responses=True)
            await self._client.ping()
            logger.info("Redis connected ✅")
        except Exception as e:
            logger.warning(f"Redis unavailable ({e}). Using in-memory cache.")
            self._client = None

    async def disconnect(self):
        if self._client:
            await self._client.aclose()

    async def get(self, key: str) -> Optional[dict]:
        try:
            if self._client:
                value = await self._client.get(key)
                if value:
                    self._hit_count += 1
                    return json.loads(value)
                self._miss_count += 1
                return None
            else:
                value = self._fallback.get(key)
                if value:
                    self._hit_count += 1
                self._miss_count += 1 if not value else 0
                return value
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    async def set(self, key: str, value: dict, ttl: int = 3600):
        try:
            if self._client:
                await self._client.setex(key, ttl, json.dumps(value))
            else:
                self._fallback[key] = value
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    async def delete(self, key: str):
        try:
            if self._client:
                await self._client.delete(key)
            else:
                self._fallback.pop(key, None)
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

    @property
    def hit_rate(self) -> float:
        total = self._hit_count + self._miss_count
        return self._hit_count / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        return {
            "hits": self._hit_count,
            "misses": self._miss_count,
            "hit_rate": round(self.hit_rate, 4),
            "backend": "redis" if self._client else "in-memory",
        }
