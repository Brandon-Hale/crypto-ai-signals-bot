"""Upstash Redis client for ephemeral state caching with command counting."""

from loguru import logger
from upstash_redis import AsyncRedis

from config import settings


class RedisClient:
    """Thin wrapper around Upstash Redis async client with per-loop command tracking."""

    def __init__(self) -> None:
        self.client = AsyncRedis(
            url=settings.upstash_redis_rest_url,
            token=settings.upstash_redis_rest_token,
        )
        self._loop_commands: int = 0
        self._total_commands: int = 0
        self._max_per_loop: int = settings.bot_max_redis_commands_per_loop

    def reset_loop_counter(self) -> None:
        """Call at the start of each strategy loop."""
        self._loop_commands = 0

    def _track(self) -> bool:
        """Track a command. Returns False if loop limit exceeded."""
        self._loop_commands += 1
        self._total_commands += 1
        if self._loop_commands > self._max_per_loop:
            logger.warning(
                f"Redis loop limit exceeded: {self._loop_commands}/{self._max_per_loop} "
                f"— skipping further commands this loop"
            )
            return False
        return True

    async def get(self, key: str) -> str | None:
        if not self._track():
            return None
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        if not self._track():
            return
        await self.client.set(key, value, ex=ex)

    async def hset(self, key: str, field: str, value: str) -> None:
        if not self._track():
            return
        await self.client.hset(key, field, value)

    async def hget(self, key: str, field: str) -> str | None:
        if not self._track():
            return None
        return await self.client.hget(key, field)

    async def hgetall(self, key: str) -> dict[str, str]:
        if not self._track():
            return {}
        result = await self.client.hgetall(key)
        return result or {}

    async def exists(self, key: str) -> bool:
        if not self._track():
            return False
        result = await self.client.exists(key)
        return result > 0

    async def zadd(self, key: str, score: float, member: str) -> None:
        if not self._track():
            return
        await self.client.zadd(key, {member: score})

    async def zrevrange(self, key: str, start: int, stop: int) -> list[str]:
        if not self._track():
            return []
        return await self.client.zrevrange(key, start, stop)

    async def incrbyfloat(self, key: str, amount: float) -> float:
        if not self._track():
            return 0.0
        return await self.client.incrbyfloat(key, amount)

    async def ping(self) -> bool:
        result = await self.client.ping()
        return result == "PONG"


redis_client = RedisClient()
