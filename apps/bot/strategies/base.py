"""Abstract base class for all trading strategies."""

from abc import ABC, abstractmethod

from clients.claude import ClaudeClient
from clients.exchange import ExchangeClient
from clients.news import NewsClient
from clients.redis import RedisClient
from clients.supabase import SupabaseClient
from config import Settings
from models.market import TechnicalIndicators
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

    async def get_cached_indicators(self, symbol: str, timeframe: str) -> TechnicalIndicators | None:
        """Get pre-computed indicators from Redis cache."""
        cached = await self.redis.get(f"pair:{symbol}:indicators:{timeframe}")
        if cached:
            return TechnicalIndicators.model_validate_json(cached)
        return None

    def calculate_stop_target(
        self,
        current_price: float,
        atr: float,
        direction: str,
        response_stop_mult: float | None,
        response_target_mult: float | None,
    ) -> tuple[float, float, float] | None:
        """Calculate stop, target, and R:R. Returns None if R:R too low."""
        stop_mult = response_stop_mult or self.settings.bot_default_stop_atr_mult
        target_mult = response_target_mult or self.settings.bot_default_target_atr_mult

        if direction == "LONG":
            stop_price = current_price - (atr * stop_mult)
            target_price = current_price + (atr * target_mult)
        else:
            stop_price = current_price + (atr * stop_mult)
            target_price = current_price - (atr * target_mult)

        stop_dist = abs(current_price - stop_price)
        target_dist = abs(target_price - current_price)
        risk_reward = target_dist / stop_dist if stop_dist > 0 else 0

        if risk_reward < self.settings.bot_min_rr:
            return None

        return stop_price, target_price, round(risk_reward, 3)
