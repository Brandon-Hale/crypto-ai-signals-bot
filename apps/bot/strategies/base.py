"""Abstract base class for all trading strategies."""

from abc import ABC, abstractmethod

from clients.claude import ClaudeClient
from clients.exchange import ExchangeClient
from clients.news import NewsClient
from clients.redis import RedisClient
from clients.supabase import SupabaseClient
from config import Settings
from models.market import Pair
from models.signal import Signal


class BaseStrategy(ABC):
    """Base class that all strategies must implement."""

    name: str

    def __init__(
        self,
        settings: Settings,
        exchange: ExchangeClient,
        claude: ClaudeClient,
        news: NewsClient,
        redis: RedisClient,
        supabase: SupabaseClient,
    ) -> None:
        self.settings = settings
        self.exchange = exchange
        self.claude = claude
        self.news = news
        self.redis = redis
        self.supabase = supabase

    @abstractmethod
    async def evaluate(self, pair: Pair) -> Signal | None:
        """Evaluate a single pair and return a signal if conditions are met."""
        ...

    async def is_deduped(self, symbol: str, direction: str) -> bool:
        """Check if a signal already fired for this pair+direction+strategy in the last 2h."""
        key = f"signals:dedup:{symbol}:{direction}:{self.name}"
        return await self.redis.exists(key)

    async def set_dedup(self, symbol: str, direction: str) -> None:
        """Set the dedup key with 2h TTL."""
        key = f"signals:dedup:{symbol}:{direction}:{self.name}"
        await self.redis.set(key, "1", ex=7200)
