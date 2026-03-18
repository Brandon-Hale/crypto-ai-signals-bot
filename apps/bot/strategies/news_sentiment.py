"""Strategy 1: News sentiment — detect mispricing relative to breaking news."""

from loguru import logger

from config import settings as app_settings
from indicators.technical import compute_indicators
from models.market import Pair
from models.signal import Signal
from strategies.base import BaseStrategy


class NewsSentimentStrategy(BaseStrategy):
    """Exploits the lag between breaking crypto news and price adjustment."""

    name = "news_sentiment"

    async def evaluate(self, pair: Pair) -> Signal | None:
        """Evaluate a pair for news-driven mispricing."""
        symbol = pair.symbol
        base = pair.base_asset

        # Fetch news
        articles = await self.news.fetch_news(base, limit=5)
        if not articles:
            return None

        # Skip if both directions already deduped
        if await self.is_deduped(symbol, "LONG") and await self.is_deduped(symbol, "SHORT"):
            return None

        # Fetch market data
        ohlcv = await self.exchange.fetch_ohlcv(symbol, "1h", limit=100)
        if not ohlcv or len(ohlcv) < 50:
            return None

        indicators = compute_indicators(ohlcv)
        order_book = await self.exchange.fetch_order_book(symbol)
        if not order_book:
            return None

        # Build order book summary
        ob_summary = {
            "best_bid": order_book.best_bid,
            "best_ask": order_book.best_ask,
            "spread_pct": order_book.spread_pct,
            "bid_depth": order_book.bid_depth_top5,
            "ask_depth": order_book.ask_depth_top5,
            "book_imbalance": order_book.book_imbalance,
        }

        headlines = [
            {"title": a.title, "source": a.source} for a in articles
        ]

        current_price = float(pair.current_price) if pair.current_price else ohlcv[-1].close

        # Ask Claude
        response = await self.claude.analyse_news_sentiment(
            symbol=symbol,
            base_asset=base,
            current_price=current_price,
            price_change_24h=float(pair.price_change_24h or 0),
            volume_24h=float(pair.volume_24h or 0),
            indicators=indicators.model_dump(),
            order_book_summary=ob_summary,
            news_headlines=headlines,
        )

        if not response or response.direction == "NONE":
            return None

        if response.confidence < app_settings.bot_min_confidence:
            return None

        # Calculate stop and target from ATR
        atr = indicators.atr_14
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

        # Check dedup for the chosen direction
        if await self.is_deduped(symbol, response.direction):
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
            news_headlines=headlines,
            indicators=indicators.model_dump(),
        )

        logger.info(
            f"Signal: {signal.direction} {symbol} | "
            f"conf={signal.confidence:.2f} rr={signal.risk_reward:.2f}"
        )
        return signal
