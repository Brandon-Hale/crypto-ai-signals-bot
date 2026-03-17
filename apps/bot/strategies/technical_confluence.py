"""Strategy 2: Technical confluence — multi-indicator alignment detection."""

from loguru import logger

from config import settings as app_settings
from indicators.technical import compute_indicators
from models.market import Pair
from models.signal import Signal
from strategies.base import BaseStrategy


class TechnicalConfluenceStrategy(BaseStrategy):
    """Generates signals when multiple technical indicators align."""

    name = "technical_confluence"

    async def evaluate(self, pair: Pair) -> Signal | None:
        """Evaluate confluence on both 1h and 4h timeframes."""
        for timeframe in ("4h", "1h"):
            signal = await self._evaluate_timeframe(pair, timeframe)
            if signal:
                return signal
        return None

    async def _evaluate_timeframe(self, pair: Pair, timeframe: str) -> Signal | None:
        symbol = pair.symbol

        ohlcv = await self.exchange.fetch_ohlcv(symbol, timeframe, limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        ind = compute_indicators(ohlcv)
        current_price = ohlcv[-1].close

        # Score LONG conditions
        long_score, long_conditions = self._score_long(ind, current_price)
        short_score, short_conditions = self._score_short(ind, current_price)

        # Pick the stronger direction
        if long_score >= 4:
            score, conditions, direction = long_score, long_conditions, "LONG"
        elif short_score >= 4:
            score, conditions, direction = short_score, short_conditions, "SHORT"
        else:
            return None

        if await self.is_deduped(symbol, direction):
            return None

        # Ask Claude to assess setup quality
        response = await self.claude.analyse_technical_confluence(
            symbol=symbol,
            current_price=current_price,
            timeframe=timeframe,
            confluence_score=score,
            direction_label=direction,
            indicators=ind.model_dump(),
            triggered_conditions=conditions,
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
            timeframe=timeframe,
            reasoning=response.reasoning,
            indicators=ind.model_dump(),
            signal_metadata={
                "confluence_score": score,
                "setup_quality": response.setup_quality or "C",
                "triggered_conditions": conditions,
            },
        )

        logger.info(
            f"Signal: {signal.direction} {symbol} {timeframe} | "
            f"confluence={score}/6 conf={signal.confidence:.2f}"
        )
        return signal

    def _score_long(
        self, ind: "TechnicalIndicators", price: float
    ) -> tuple[int, list[str]]:
        score = 0
        conditions: list[str] = []

        if ind.rsi_14 < 40:
            score += 1
            conditions.append(f"RSI trending up from {ind.rsi_14:.1f}")
        if ind.rsi_14 < 30:
            score += 1
            conditions.append(f"RSI oversold at {ind.rsi_14:.1f}")
        if ind.macd_hist > 0 and ind.macd > ind.macd_signal:
            score += 1
            conditions.append("MACD crossed above signal line")
        if ind.bb_pct <= 0.05:
            score += 1
            conditions.append(f"Price near lower Bollinger Band (BB%={ind.bb_pct:.2f})")
        if price > ind.ema_20 > ind.ema_50:
            score += 1
            conditions.append("Bullish EMA alignment: Price > EMA20 > EMA50")
        if ind.volume_sma_20 > 0 and ind.current_volume > 1.5 * ind.volume_sma_20:
            score += 1
            conditions.append(
                f"Volume confirmation: {ind.current_volume / ind.volume_sma_20:.1f}x average"
            )

        return score, conditions

    def _score_short(
        self, ind: "TechnicalIndicators", price: float
    ) -> tuple[int, list[str]]:
        score = 0
        conditions: list[str] = []

        if ind.rsi_14 > 60:
            score += 1
            conditions.append(f"RSI trending down from {ind.rsi_14:.1f}")
        if ind.rsi_14 > 70:
            score += 1
            conditions.append(f"RSI overbought at {ind.rsi_14:.1f}")
        if ind.macd_hist < 0 and ind.macd < ind.macd_signal:
            score += 1
            conditions.append("MACD crossed below signal line")
        if ind.bb_pct >= 0.95:
            score += 1
            conditions.append(f"Price near upper Bollinger Band (BB%={ind.bb_pct:.2f})")
        if price < ind.ema_20 < ind.ema_50:
            score += 1
            conditions.append("Bearish EMA alignment: Price < EMA20 < EMA50")
        if ind.volume_sma_20 > 0 and ind.current_volume > 1.5 * ind.volume_sma_20:
            score += 1
            conditions.append(
                f"Volume confirmation: {ind.current_volume / ind.volume_sma_20:.1f}x average"
            )

        return score, conditions
