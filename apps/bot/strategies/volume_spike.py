"""Strategy 3: Volume spike detection — unusual order flow as a leading indicator."""

from loguru import logger

from config import settings as app_settings
from indicators.technical import compute_indicators
from models.market import Pair
from models.signal import Signal
from strategies.base import BaseStrategy


class VolumeSpikeStrategy(BaseStrategy):
    """Detects unusual volume concentration that may indicate informed trading."""

    name = "volume_spike"

    async def evaluate(self, pair: Pair) -> Signal | None:
        """Check for volume spikes and order flow imbalances."""
        symbol = pair.symbol

        ohlcv = await self.exchange.fetch_ohlcv(symbol, "1h", limit=100)
        if not ohlcv or len(ohlcv) < 25:
            return None

        ind = compute_indicators(ohlcv)

        # Check volume spike threshold
        if ind.volume_sma_20 <= 0:
            return None
        volume_ratio = ind.current_volume / ind.volume_sma_20
        if volume_ratio < 2.5:
            return None

        logger.debug(f"{symbol}: Volume spike detected — {volume_ratio:.1f}x average")

        # Fetch order book and recent trades
        order_book = await self.exchange.fetch_order_book(symbol)
        recent_trades = await self.exchange.fetch_recent_trades(symbol, limit=50)
        if not order_book or not recent_trades:
            return None

        # Calculate buy/sell pressure from recent trades
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

        # Determine direction from trade pressure
        if buy_pressure >= 0.65:
            direction = "LONG"
        elif buy_pressure <= 0.35:
            direction = "SHORT"
        else:
            return None  # Indeterminate

        # Check order book imbalance
        book_imbalance = order_book.book_imbalance
        if direction == "LONG" and book_imbalance < 1.0:
            return None  # Book doesn't support the direction
        if direction == "SHORT" and book_imbalance > 1.0:
            return None

        if await self.is_deduped(symbol, direction):
            return None

        # Fetch recent news for context
        articles = await self.news.fetch_news(pair.base_asset, limit=3)
        news_summary = (
            "; ".join(a.title for a in articles) if articles else "No recent news found."
        )

        # Ask Claude for final assessment
        current_price = ohlcv[-1].close
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

        atr = ind.atr_14
        stop_mult = response.suggested_stop_atr_mult or app_settings.bot_default_stop_atr_mult
        target_mult = response.suggested_target_atr_mult or app_settings.bot_default_target_atr_mult

        if response.direction == "LONG":
            stop_price = current_price - (atr * stop_mult)
            target_price = current_price + (atr * target_mult)
        else:
            stop_price = current_price + (atr * stop_mult)
            target_price = current_price - (atr * target_mult)

        stop_dist = abs(current_price - stop_price)
        target_dist = abs(target_price - current_price)
        risk_reward = target_dist / stop_dist if stop_dist > 0 else 0

        if risk_reward < app_settings.bot_min_rr:
            return None

        await self.set_dedup(symbol, response.direction)

        signal = Signal(
            pair_id=pair.id or "",
            strategy=self.name,
            direction=response.direction,
            confidence=response.confidence,
            entry_price=current_price,
            target_price=target_price,
            stop_price=stop_price,
            risk_reward=round(risk_reward, 3),
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
