"""APScheduler job definitions for the strategy loop."""

import asyncio
import json
from datetime import datetime, timezone

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

            # Heartbeat expires after 2x the loop interval — if the bot dies, this key vanishes
            heartbeat_ttl = self.settings.bot_strategy_interval_minutes * 2 * 60
            await self.redis.set("bot:heartbeat", "1", ex=heartbeat_ttl)

            # Check for pause/resume command from dashboard
            command = await self.redis.get("bot:command")
            if command == "pause":
                await self.redis.set("bot:status", "paused")
                logger.info("Bot paused via dashboard — skipping loop")
                return
            elif command == "resume":
                # Clear the command and continue with the loop
                await self.redis.set("bot:command", "")
                logger.info("Bot resumed via dashboard")

            await self.redis.set("bot:status", "running")
            logger.info("Strategy loop starting")

            # 1. Fetch active pairs
            pairs = await self._fetch_active_pairs()
            if not pairs:
                logger.warning("No active pairs found")
                return

            # 2. Update Redis prices
            await self._update_redis_prices(pairs)

            # 3. Pre-compute indicators for all pairs and timeframes
            await self._precompute_all_indicators(pairs)

            # 4. Pre-fetch news for all unique base assets
            await self._prefetch_all_news(pairs)

            # 5. Run all strategies (parallelized per pair)
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

            # Upsert pairs to Supabase so each gets a UUID
            persisted_pairs: list[Pair] = []
            for pair in pairs:
                row = await self.supabase.upsert(
                    "pairs",
                    {
                        "symbol": pair.symbol,
                        "base_asset": pair.base_asset,
                        "quote_asset": pair.quote_asset,
                        "category": pair.category,
                        "current_price": float(pair.current_price) if pair.current_price else None,
                        "price_change_24h": float(pair.price_change_24h) if pair.price_change_24h else None,
                        "volume_24h": float(pair.volume_24h) if pair.volume_24h else None,
                        "is_active": True,
                    },
                    on_conflict="symbol",
                )
                if row:
                    pair.id = row["id"]
                    persisted_pairs.append(pair)
                else:
                    logger.warning(f"Failed to upsert pair {pair.symbol} — skipping")

            # Cache active pair list and UUID→symbol mapping
            await self.redis.set(
                "pairs:active",
                json.dumps([p.symbol for p in persisted_pairs]),
            )
            for p in persisted_pairs:
                if p.id:
                    await self.redis.hset("pairs:id_to_symbol", p.id, p.symbol)

            return persisted_pairs
        except Exception as e:
            logger.error(f"Failed to fetch active pairs: {e}")
            return []

    async def _update_redis_prices(self, pairs: list[Pair]) -> None:
        """Write current prices to Redis hashes (by symbol and by UUID)."""
        for pair in pairs:
            if pair.current_price is not None:
                price_str = str(pair.current_price)
                await self.redis.hset("pairs:prices", pair.symbol, price_str)
                if pair.id:
                    await self.redis.hset("pairs:prices_by_id", pair.id, price_str)

    async def _precompute_all_indicators(self, pairs: list[Pair]) -> None:
        """Pre-compute indicators for all pairs across all needed timeframes.

        Strategies read from cache instead of computing independently.
        This eliminates ~90% of redundant OHLCV fetches and indicator computations.
        """
        timeframes = ["1h", "4h"]

        async def compute_for(pair: Pair, tf: str) -> None:
            cache_key = f"pair:{pair.symbol}:indicators:{tf}"
            # Skip if already cached (within 5 min TTL)
            existing = await self.redis.get(cache_key)
            if existing:
                return
            try:
                ohlcv = await self.exchange.fetch_ohlcv(pair.symbol, tf, limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    return
                indicators = compute_indicators(ohlcv)
                await self.redis.set(cache_key, indicators.model_dump_json(), ex=300)
            except Exception as e:
                logger.warning(f"Indicator pre-compute failed for {pair.symbol} {tf}: {e}")

        # Parallelize indicator computation (batched to avoid overwhelming exchange)
        batch_size = 10
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            tasks = [
                compute_for(pair, tf)
                for pair in batch
                for tf in timeframes
            ]
            await asyncio.gather(*tasks)

    async def _prefetch_all_news(self, pairs: list[Pair]) -> None:
        """Pre-fetch news for all unique base assets so strategies don't re-fetch."""
        seen_assets: set[str] = set()
        for pair in pairs:
            if pair.base_asset not in seen_assets:
                seen_assets.add(pair.base_asset)
                try:
                    await self.news.fetch_news(pair.base_asset, limit=5)
                except Exception as e:
                    logger.debug(f"News prefetch failed for {pair.base_asset}: {e}")

    async def _run_all_strategies(self, pairs: list[Pair]) -> None:
        """Execute all strategies across all pairs, parallelized per pair."""
        _exclude_fields = {"id", "created_at", "symbol"}

        async def evaluate_pair(pair: Pair) -> None:
            for strategy in self.strategies:
                try:
                    signal = await strategy.evaluate(pair)
                    if signal:
                        signal.pair_id = signal.pair_id or pair.id
                        signal.symbol = signal.symbol or pair.symbol

                        signal_data = {
                            k: v
                            for k, v in signal.model_dump().items()
                            if k not in _exclude_fields and v is not None
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

        # Run pairs in parallel batches to avoid overwhelming APIs
        batch_size = 5
        for i in range(0, len(pairs), batch_size):
            batch = pairs[i : i + batch_size]
            await asyncio.gather(*[evaluate_pair(p) for p in batch])

    async def _get_current_prices(self) -> dict[str, float]:
        """Get current prices from Redis, keyed by pair UUID."""
        prices_map = await self.redis.hgetall("pairs:prices_by_id")
        return {pair_id: float(price) for pair_id, price in prices_map.items()}

    async def _update_equity_snapshot(self) -> None:
        """Write current equity to equity_snapshots table."""
        equity_str = await self.redis.get("bot:paper:equity")
        if not equity_str:
            # Backfill from closed trades if Redis has no equity yet
            closed_trades = await self.supabase.select(
                "trades", filters={"mode": "paper", "status": "closed"}
            )
            total_pnl = sum(float(t.get("pnl_usd", 0)) for t in closed_trades)
            equity = 10000.0 + total_pnl
            await self.redis.set("bot:paper:equity", str(round(equity, 2)))
            logger.info(f"Backfilled paper equity from {len(closed_trades)} closed trades: ${equity:.2f}")
        else:
            equity = float(equity_str)

        await self.supabase.insert(
            "equity_snapshots",
            {
                "mode": self.trader.mode,
                "equity_usd": equity,
            },
        )

    async def _update_performance_summary(self) -> None:
        """Recalculate win rate, P&L, drawdown per strategy."""
        try:
            trades = await self.supabase.select(
                "trades",
                filters={"status": "closed"},
            )
            if not trades:
                return

            # Build signal_id → strategy mapping so we can attribute trades
            signals = await self.supabase.select("signals", columns="id,strategy")
            signal_strategy = {s["id"]: s["strategy"] for s in signals}

            for strategy in self.strategies:
                try:
                    strategy_trades = [
                        t for t in trades
                        if signal_strategy.get(t.get("signal_id")) == strategy.name
                    ]

                    if not strategy_trades:
                        continue

                    winning = sum(1 for t in strategy_trades if float(t.get("pnl_usd", 0)) > 0)
                    total = len(strategy_trades)
                    total_pnl = sum(float(t.get("pnl_usd", 0)) for t in strategy_trades)

                    await self.supabase.upsert(
                        "performance_summary",
                        {
                            "strategy": strategy.name,
                            "timeframe": "all",
                            "total_trades": total,
                            "winning_trades": winning,
                            "losing_trades": total - winning,
                            "total_pnl_usd": round(total_pnl, 2),
                            "win_rate": round(winning / total, 4) if total > 0 else 0,
                        },
                        on_conflict="strategy,timeframe",
                    )
                except Exception as e:
                    logger.warning(f"Performance update failed for {strategy.name}: {e}")
        except Exception as e:
            logger.warning(f"Performance summary fetch failed: {e}")
