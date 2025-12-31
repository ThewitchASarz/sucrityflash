"""
Redis client for approval queue, rate limiting, and caching.
"""
import redis.asyncio as redis
from config import settings
from typing import Optional


class RedisClient:
    """Async Redis client wrapper."""

    def __init__(self):
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Establish Redis connection."""
        self.client = await redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set key-value pair with optional expiration (seconds)."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        await self.client.set(key, value, ex=ex)

    async def delete(self, key: str):
        """Delete key."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        await self.client.delete(key)

    async def incr(self, key: str) -> int:
        """Increment key value."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int):
        """Set expiration on key."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        await self.client.expire(key, seconds)

    async def zadd(self, key: str, mapping: dict):
        """Add to sorted set."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        await self.client.zadd(key, mapping)

    async def zrangebyscore(self, key: str, min_score: float, max_score: float):
        """Get sorted set members by score range."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        return await self.client.zrangebyscore(key, min_score, max_score)

    async def zrem(self, key: str, *members):
        """Remove members from sorted set."""
        if not self.client:
            raise RuntimeError("Redis client not connected")
        await self.client.zrem(key, *members)


# Global Redis client instance
redis_client = RedisClient()
