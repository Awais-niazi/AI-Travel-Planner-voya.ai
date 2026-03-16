import json
from typing import Any

import redis.asyncio as aioredis

from app.core.config import settings

# TTLs in seconds
TTL_ITINERARY = 60 * 60 * 24       # 24 hours
TTL_RECOMMENDATIONS = 60 * 60 * 6  # 6 hours
TTL_SEARCH = 60 * 60               # 1 hour
TTL_POPULAR = 60 * 30              # 30 minutes


class CacheService:
    def __init__(self):
        self._client: aioredis.Redis | None = None

    async def client(self) -> aioredis.Redis:
        if self._client is None:
            self._client = await aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def get(self, key: str) -> Any | None:
        r = await self.client()
        value = await r.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(self, key: str, value: Any, ttl: int = TTL_SEARCH) -> None:
        r = await self.client()
        await r.setex(key, ttl, json.dumps(value))

    async def delete(self, key: str) -> None:
        r = await self.client()
        await r.delete(key)

    async def delete_pattern(self, pattern: str) -> None:
        r = await self.client()
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)

    # ── Typed helpers ──────────────────────────────────────────────────

    async def get_itinerary(self, trip_id: str) -> dict | None:
        return await self.get(f"itinerary:{trip_id}")

    async def set_itinerary(self, trip_id: str, data: dict) -> None:
        await self.set(f"itinerary:{trip_id}", data, TTL_ITINERARY)

    async def get_recommendations(self, destination: str, interests_key: str) -> list | None:
        return await self.get(f"recs:{destination}:{interests_key}")

    async def set_recommendations(
        self, destination: str, interests_key: str, data: list
    ) -> None:
        await self.set(f"recs:{destination}:{interests_key}", data, TTL_RECOMMENDATIONS)

    async def invalidate_trip(self, trip_id: str) -> None:
        await self.delete_pattern(f"*:{trip_id}*")

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()


cache = CacheService()