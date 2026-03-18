"""Strategy 1: News sentiment — detect mispricing relative to breaking news."""

from loguru import logger

from config import settings as app_settings
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

        # 1. Early dedup check — before any data fetching
        if await self.is_deduped(symbol, "LONG") and await self.is_deduped(symbol, "SHORT"):
            return None

        # 2. Fetch news (pre-fetched by scheduler, should be cached)
        articles = await self.news.fetch_news(base, limit=5)
        if not articles:
            return None

        # 3. Get pre-computed indicators from cache
        indicators = await self.get_cached_indicators(symbol, "1h")
        if not indicators:
            return None

        # 4. Fetch order book
        order_book = await self.exchange.fetch_order_book(symbol)
        if not order_book:
            return None

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

        current_price = float(pair.current_price) if pair.current_price else 0
        if current_price <= 0:
            return None

        # 5. Ask Claude
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

        # 6. Check dedup for the chosen direction
        if await self.is_deduped(symbol, response.direction):
            return None

        # 7. Calculate stop/target
        result = self.calculate_stop_target(
            current_price, indicators.atr_14, response.direction,
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
            news_headlines=headlines,
            indicators=indicators.model_dump(),
        )

        logger.info(
            f"Signal: {signal.direction} {symbol} | "
            f"conf={signal.confidence:.2f} rr={signal.risk_reward:.2f}"
        )
        return signal
