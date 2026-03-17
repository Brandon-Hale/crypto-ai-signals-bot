"""Upstash Redis client for ephemeral state caching."""

from upstash_redis import AsyncRedis

from config import settings


class RedisClient:
    """Thin wrapper around Upstash Redis async client."""

    def __init__(self) -> None:
        self.client = AsyncRedis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
        )

    async def get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        await self.client.set(key, value, ex=ex)

    async def hset(self, key: str, field: str, value: str) -> None:
        await self.client.hset(key, {field: value})

    async def hget(self, key: str, field: str) -> str | None:
        return await self.client.hget(key, field)

    async def hgetall(self, key: str) -> dict[str, str]:
        result = await self.client.hgetall(key)
        return result or {}

    async def exists(self, key: str) -> bool:
        result = await self.client.exists(key)
        return result > 0

    async def zadd(self, key: str, score: float, member: str) -> None:
        await self.client.zadd(key, {member: score})

    async def zrevrange(self, key: str, start: int, stop: int) -> list[str]:
        return await self.client.zrevrange(key, start, stop)

    async def incrbyfloat(self, key: str, amount: float) -> float:
        return await self.client.incrbyfloat(key, amount)

    async def ping(self) -> bool:
        result = await self.client.ping()
        return result == "PONG"


redis_client = RedisClient()
