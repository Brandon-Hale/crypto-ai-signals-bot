"""Strategy 3: Volume spike detection — unusual order flow as a leading indicator."""

from loguru import logger

from config import settings as app_settings
from models.market import Pair
from models.signal import Signal
from strategies.base import BaseStrategy


class VolumeSpikeStrategy(BaseStrategy):
    """Detects unusual volume concentration that may indicate informed trading."""

    name = "volume_spike"

    async def evaluate(self, pair: Pair) -> Signal | None:
        """Check for volume spikes and order flow imbalances."""
        symbol = pair.symbol

        # 1. Get pre-computed indicators from cache
        ind = await self.get_cached_indicators(symbol, "1h")
        if not ind:
            return None

        # 2. Check volume spike threshold — no API calls needed
        if ind.volume_sma_20 <= 0:
            return None
        volume_ratio = ind.current_volume / ind.volume_sma_20
        if volume_ratio < 3.0:  # Tightened from 2.5 — only strong spikes worth Claude's time
            return None

        logger.debug(f"{symbol}: Volume spike detected — {volume_ratio:.1f}x average")

        # 3. Fetch order book and recent trades for direction determination
        order_book = await self.exchange.fetch_order_book(symbol)
        recent_trades = await self.exchange.fetch_recent_trades(symbol, limit=50)
        if not order_book or not recent_trades:
            return None

        # 4. Calculate buy/sell pressure from recent trades
        buy_volume = sum(
            float(t.get("amount", 0))
            for t in recent_trades
            if t.get("side") == "buy"
        )
        sell_volume = sum(
            float(t.get("amount", 0))
            for t in recent_trades
            if t.get("side") == "sell"
        )
        total = buy_volume + sell_volume
        buy_pressure = buy_volume / total if total > 0 else 0.5

        # 5. Determine direction from trade pressure
        if buy_pressure >= 0.65:
            direction = "LONG"
        elif buy_pressure <= 0.35:
            direction = "SHORT"
        else:
            return None  # Indeterminate

        # 6. Check order book imbalance confirms direction
        book_imbalance = order_book.book_imbalance
        if direction == "LONG" and book_imbalance < 1.0:
            return None
        if direction == "SHORT" and book_imbalance > 1.0:
            return None

        # 7. Early dedup check — after direction is known, before Claude call
        if await self.is_deduped(symbol, direction):
            return None

        # 8. Fetch recent news for context (pre-fetched by scheduler, should be cached)
        articles = await self.news.fetch_news(pair.base_asset, limit=3)
        news_summary = (
            "; ".join(a.title for a in articles) if articles else "No recent news found."
        )

        # 9. Ask Claude for final assessment
        current_price = float(pair.current_price) if pair.current_price else 0
        if current_price <= 0:
            return None

        response = await self.claude.analyse_volume_spike(
            symbol=symbol,
            current_price=current_price,
            volume_ratio=volume_ratio,
            buy_pressure=buy_pressure,
            book_imbalance=book_imbalance,
            indicators=ind.model_dump(),
            recent_news_summary=news_summary,
        )

        if not response or response.direction == "NONE":
            return None
        if response.confidence < app_settings.bot_min_confidence:
            return None

        # 10. Calculate stop/target
        result = self.calculate_stop_target(
            current_price, ind.atr_14, response.direction,
            response.suggested_stop_atr_mult, response.suggested_target_atr_mult,
        )
        if not result:
            return None
        stop_price, target_price, risk_reward = result

        await self.set_dedup(symbol, response.direction)

        signal = Signal(
            pair_id=pair.id or "",
            strategy=self.name,
            direction=response.direction,
            confidence=response.confidence,
            entry_price=current_price,
            target_price=target_price,
            stop_price=stop_price,
            risk_reward=risk_reward,
            edge_pct=response.edge_pct,
            timeframe="1h",
            reasoning=response.reasoning,
            indicators=ind.model_dump(),
            signal_metadata={
                "volume_ratio": round(volume_ratio, 2),
                "buy_pressure": round(buy_pressure, 3),
                "book_imbalance": round(book_imbalance, 3),
            },
        )

        logger.info(
            f"Signal: {signal.direction} {symbol} | "
            f"vol={volume_ratio:.1f}x buy_pres={buy_pressure:.2f}"
        )
        return signal
