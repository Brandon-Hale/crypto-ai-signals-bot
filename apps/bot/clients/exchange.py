"""Exchange client using ccxt — Binance by default, configurable via env."""

import asyncio
import json

import ccxt.async_support as ccxt
from loguru import logger

from clients.redis import RedisClient
from config import Settings
from models.market import OHLCV, OrderBook, OrderBookLevel


class ExchangeClient:
    """Unified exchange client with Redis caching and retry logic."""

    def __init__(self, settings: Settings, redis: RedisClient) -> None:
        exchange_class = getattr(ccxt, settings.exchange_id)
        self.exchange: ccxt.Exchange = exchange_class(
            {
                "apiKey": settings.exchange_api_key or None,
                "secret": settings.exchange_api_secret or None,
                "enableRateLimit": True,
                "options": {"defaultType": settings.exchange_market_type},
            }
        )
        self.redis = redis
        self._max_retries = 3

    async def close(self) -> None:
        await self.exchange.close()

    async def _retry(self, coro_factory, retries: int | None = None):
        """Execute an async callable with exponential backoff on transient errors."""
        max_retries = retries or self._max_retries
        for attempt in range(max_retries):
            try:
                return await coro_factory()
            except ccxt.RateLimitExceeded:
                wait = 2**attempt
                logger.warning(f"Rate limited, waiting {wait}s (attempt {attempt + 1})")
                await asyncio.sleep(wait)
            except (ccxt.NetworkError, ccxt.ExchangeNotAvailable) as e:
                wait = 2**attempt
                logger.warning(f"Network error: {e}, retrying in {wait}s")
                await asyncio.sleep(wait)
        logger.error(f"All {max_retries} retries exhausted")
        return None

    async def fetch_ticker(self, symbol: str) -> dict | None:
        """Fetch current ticker data for a symbol."""

        async def _call():
            return await self.exchange.fetch_ticker(symbol)

        return await self._retry(_call)

    async def fetch_ohlcv(
        self, symbol: str, timeframe: str = "1h", limit: int = 200
    ) -> list[OHLCV] | None:
        """Fetch OHLCV candles, checking Redis cache first."""
        cache_key = f"pair:{symbol}:ohlcv:{timeframe}"
        cached = await self.redis.get(cache_key)
        if cached:
            try:
                data = json.loads(cached)
                return [OHLCV(**c) for c in data]
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Corrupted OHLCV cache for {symbol}: {e}")
                # Fall through to fetch from exchange

        async def _call():
            return await self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

        raw = await self._retry(_call)
        if raw is None:
            return None

        candles = [
            OHLCV(
                timestamp=candle[0],
                open=candle[1],
                high=candle[2],
                low=candle[3],
                close=candle[4],
                volume=candle[5],
            )
            for candle in raw
        ]

        # Cache for 60 seconds
        await self.redis.set(
            cache_key,
            json.dumps([c.model_dump(mode="json") for c in candles]),
            ex=60,
        )
        return candles

    async def fetch_order_book(
        self, symbol: str, limit: int = 20
    ) -> OrderBook | None:
        """Fetch order book, checking Redis cache first."""
        cache_key = f"pair:{symbol}:orderbook"
        cached = await self.redis.get(cache_key)
        if cached:
            try:
                return OrderBook(**json.loads(cached))
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Corrupted order book cache for {symbol}: {e}")

        async def _call():
            return await self.exchange.fetch_order_book(symbol, limit=limit)

        raw = await self._retry(_call)
        if raw is None:
            return None

        book = OrderBook(
            symbol=symbol,
            bids=[OrderBookLevel(price=b[0], amount=b[1]) for b in raw["bids"]],
            asks=[OrderBookLevel(price=a[0], amount=a[1]) for a in raw["asks"]],
        )

        await self.redis.set(cache_key, book.model_dump_json(), ex=15)
        return book

    async def fetch_recent_trades(self, symbol: str, limit: int = 50) -> list[dict] | None:
        """Fetch recent trades for a symbol."""
        cache_key = f"pair:{symbol}:recent_trades"
        cached = await self.redis.get(cache_key)
        if cached:
            try:
                return json.loads(cached)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Corrupted trades cache for {symbol}: {e}")

        async def _call():
            return await self.exchange.fetch_trades(symbol, limit=limit)

        trades = await self._retry(_call)
        if trades is None:
            return None

        await self.redis.set(cache_key, json.dumps(trades, default=str), ex=30)
        return trades

    async def create_limit_order(
        self, symbol: str, side: str, amount: float, price: float
    ) -> dict | None:
        """Place a limit order (live mode only)."""

        async def _call():
            return await self.exchange.create_limit_order(symbol, side, amount, price)

        return await self._retry(_call)

    async def create_market_order(
        self, symbol: str, side: str, amount: float
    ) -> dict | None:
        """Place a market order (live mode only)."""

        async def _call():
            return await self.exchange.create_market_order(symbol, side, amount)

        return await self._retry(_call)

    async def cancel_order(self, order_id: str, symbol: str) -> dict | None:
        """Cancel an open order."""

        async def _call():
            return await self.exchange.cancel_order(order_id, symbol)

        return await self._retry(_call)

    async def fetch_order(self, order_id: str, symbol: str) -> dict | None:
        """Check order fill status."""

        async def _call():
            return await self.exchange.fetch_order(order_id, symbol)

        return await self._retry(_call)

    async def fetch_balance(self) -> dict | None:
        """Fetch account balances (live mode only)."""

        async def _call():
            return await self.exchange.fetch_balance()

        return await self._retry(_call)
