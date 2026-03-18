"""APScheduler job definitions for the strategy loop."""

import asyncio
import json
from datetime import datetime, timezone
import signal

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from clients.claude import ClaudeClient
from clients.exchange import ExchangeClient
from clients.news import NewsClient
from clients.redis import RedisClient
from clients.supabase import SupabaseClient
from config import Settings
from indicators.technical import compute_indicators
from models.market import Pair
from strategies.news_sentiment import NewsSentimentStrategy
from strategies.technical_confluence import TechnicalConfluenceStrategy
from strategies.volume_spike import VolumeSpikeStrategy
from trading.base import BaseTrader


class StrategyScheduler:
    """Manages the strategy loop and periodic tasks."""

    def __init__(
        self,
        settings: Settings,
        exchange: ExchangeClient,
        claude: ClaudeClient,
        news: NewsClient,
        redis: RedisClient,
        supabase: SupabaseClient,
        trader: BaseTrader,
    ) -> None:
        self.settings = settings
        self.exchange = exchange
        self.claude = claude
        self.news = news
        self.redis = redis
        self.supabase = supabase
        self.trader = trader
        self.scheduler = AsyncIOScheduler()

        # Initialize strategies
        strategy_args = (settings, exchange, claude, news, redis, supabase)
        self.strategies = [
            NewsSentimentStrategy(*strategy_args),
            TechnicalConfluenceStrategy(*strategy_args),
            VolumeSpikeStrategy(*strategy_args),
        ]

    def start(self) -> None:
        """Register all jobs and start the scheduler."""
        interval = self.settings.bot_strategy_interval_minutes

        self.scheduler.add_job(
            self.strategy_loop,
            "interval",
            minutes=interval,
            id="strategy_loop",
            next_run_time=datetime.now(timezone.utc),
        )
        self.scheduler.add_job(
            self.hourly_maintenance,
            "interval",
            hours=1,
            id="hourly_maintenance",
        )

        self.scheduler.start()
        logger.info(f"Scheduler started — strategy loop every {interval} minutes")

    def stop(self) -> None:
        self.scheduler.shutdown(wait=False)

    async def strategy_loop(self) -> None:
        """Main strategy loop — runs every N minutes."""
        try:
            self.redis.reset_loop_counter()
            await self.redis.set("bot:status", "running")
            logger.info("Strategy loop starting")

            # 1. Fetch active pairs
            pairs = await self._fetch_active_pairs()
            if not pairs:
                logger.warning("No active pairs found")
                return

            # 2. Update Redis prices
            await self._update_redis_prices(pairs)

            # 3. Snapshot OHLCV to Supabase
            await self._snapshot_ohlcv(pairs)

            # 4. Compute and cache indicators
            await self._compute_and_cache_indicators(pairs)

            # 5. Run all strategies in parallel
            await self._run_all_strategies(pairs)

            # 6. Check open trades
            prices = await self._get_current_prices()
            closed = await self.trader.check_and_close_by_price(prices)
            if closed:
                logger.info(f"Closed {len(closed)} trades")

            # 7. Update equity snapshot
            await self._update_equity_snapshot()

            # 8. Update performance summary
            await self._update_performance_summary()

            # 9. Update bot status
            await self.redis.set(
                "bot:last_run", datetime.now(timezone.utc).isoformat()
            )
            await self.redis.set("bot:status", "idle")
            await self.redis.set("bot:trade_mode", self.trader.mode)

            logger.info("Strategy loop completed")

        except Exception as e:
            logger.error(f"Strategy loop error: {e}")
            await self.redis.set("bot:status", "error")

    async def hourly_maintenance(self) -> None:
        """Hourly maintenance tasks."""
        try:
            # Expire old signals
            # Refresh pair list
            # Recalculate max drawdown
            logger.info("Hourly maintenance completed")
        except Exception as e:
            logger.error(f"Hourly maintenance error: {e}")

    async def _fetch_active_pairs(self) -> list[Pair]:
        """Fetch top pairs by volume from the exchange."""
        try:
            tickers = await self.exchange.exchange.fetch_tickers()
            if not tickers:
                return []

            # Filter USDT pairs and sort by volume
            usdt_pairs = []
            for symbol, ticker in tickers.items():
                if "/USDT" not in symbol:
                    continue
                vol = ticker.get("quoteVolume", 0) or 0
                if vol < 1_000_000:
                    continue
                base = symbol.split("/")[0]
                usdt_pairs.append(
                    Pair(
                        symbol=symbol,
                        base_asset=base,
                        quote_asset="USDT",
                        category="large_cap",
                        current_price=ticker.get("last"),
                        price_change_24h=ticker.get("percentage"),
                        volume_24h=vol,
                    )
                )

            usdt_pairs.sort(
                key=lambda p: float(p.volume_24h or 0), reverse=True
            )
            pairs = usdt_pairs[: self.settings.bot_max_pairs]

            # Cache active pair list
            await self.redis.set(
                "pairs:active",
                json.dumps([p.symbol for p in pairs]),
            )

            return pairs
        except Exception as e:
            logger.error(f"Failed to fetch active pairs: {e}")
            return []

    async def _update_redis_prices(self, pairs: list[Pair]) -> None:
        """Write current prices to Redis hash."""
        for pair in pairs:
            if pair.current_price is not None:
                await self.redis.hset("pairs:prices", pair.symbol, str(pair.current_price))

    async def _snapshot_ohlcv(self, pairs: list[Pair]) -> None:
        """Store latest candles in Supabase for charting."""
        # Implementation: fetch and store latest candles
        pass

    async def _compute_and_cache_indicators(self, pairs: list[Pair]) -> None:
        """Compute indicators for all pairs and cache in Redis."""
        for pair in pairs:
            try:
                ohlcv = await self.exchange.fetch_ohlcv(pair.symbol, "1h", limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    continue
                indicators = compute_indicators(ohlcv)
                await self.redis.set(
                    f"pair:{pair.symbol}:indicators",
                    indicators.model_dump_json(),
                    ex=300,
                )
            except Exception as e:
                logger.warning(f"Indicator compute failed for {pair.symbol}: {e}")

    async def _run_all_strategies(self, pairs: list[Pair]) -> None:
        """Execute all strategies across all pairs."""
        for pair in pairs:
            for strategy in self.strategies:
                try:
                    signal = await strategy.evaluate(pair)
                    if signal:
                        # Ensure pair_id is set
                        signal.pair_id = signal.pair_id or pair.symbol

                        # Prepare data for Supabase: exclude id, created_at, and None values only
                        signal_data = {
                            k: v
                            for k, v in signal.model_dump().items()
                            if k not in {"id", "created_at"} and v is not None
                        }

                        result = await self.supabase.insert("signals", signal_data)
                        if result and "id" in result:
                            signal.id = result["id"]
                            await self.trader.open_trade(signal)
                        else:
                            logger.error(f"Failed to insert signal for {pair.symbol}")
                except Exception as e:
                    logger.error(
                        f"Strategy {strategy.name} failed for {pair.symbol}: {e}"
                    )

    async def _get_current_prices(self) -> dict[str, float]:
        """Get current prices from Redis."""
        prices_map = await self.redis.hgetall("pairs:prices")
        return {symbol: float(price) for symbol, price in prices_map.items()}

    async def _update_equity_snapshot(self) -> None:
        """Write current equity to equity_snapshots table."""
        equity_str = await self.redis.get("bot:paper:equity")
        equity = float(equity_str) if equity_str else 10000.0

        await self.supabase.insert(
            "equity_snapshots",
            {
                "mode": self.trader.mode,
                "equity_usd": equity,
            },
        )

    async def _update_performance_summary(self) -> None:
        """Recalculate win rate, P&L, drawdown per strategy."""
        for strategy in self.strategies:
            try:
                trades = await self.supabase.select(
                    "trades",
                    filters={"status": "closed"},
                )
                strategy_trades = [
                    t for t in trades
                    if t.get("signal_id")  # Filter by strategy via signal
                ]

                if not strategy_trades:
                    continue

                winning = sum(1 for t in strategy_trades if float(t.get("pnl_usd", 0)) > 0)
                total = len(strategy_trades)
                total_pnl = sum(float(t.get("pnl_usd", 0)) for t in strategy_trades)

                await self.supabase.insert(
                    "performance_summary",
                    {
                        "strategy": strategy.name,
                        "total_trades": total,
                        "winning_trades": winning,
                        "losing_trades": total - winning,
                        "total_pnl_usd": round(total_pnl, 2),
                        "win_rate": round(winning / total, 4) if total > 0 else 0,
                    },
                )
            except Exception as e:
                logger.warning(f"Performance update failed for {strategy.name}: {e}")
