"""Anthropic Claude client for AI signal generation with rate limiting."""

import json
from datetime import datetime, timezone

import anthropic
from loguru import logger

from config import settings
from models.signal import ClaudeSignalResponse


class ClaudeClient:
    """Handles all Claude API interactions for signal generation."""

    MODEL = "claude-sonnet-4-20250514"

    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._hourly_calls: int = 0
        self._daily_calls: int = 0
        self._current_hour: int = datetime.now(timezone.utc).hour
        self._current_day: int = datetime.now(timezone.utc).day

    def _check_and_reset_counters(self) -> None:
        """Reset counters on hour/day rollover."""
        now = datetime.now(timezone.utc)
        if now.day != self._current_day:
            self._daily_calls = 0
            self._hourly_calls = 0
            self._current_day = now.day
            self._current_hour = now.hour
        elif now.hour != self._current_hour:
            self._hourly_calls = 0
            self._current_hour = now.hour

    def _is_rate_limited(self) -> bool:
        """Check if we've hit the hourly or daily Claude call limit."""
        self._check_and_reset_counters()
        if self._hourly_calls >= settings.bot_max_claude_calls_per_hour:
            logger.warning(
                f"Claude hourly limit reached: {self._hourly_calls}/{settings.bot_max_claude_calls_per_hour}"
            )
            return True
        if self._daily_calls >= settings.bot_max_claude_calls_per_day:
            logger.warning(
                f"Claude daily limit reached: {self._daily_calls}/{settings.bot_max_claude_calls_per_day}"
            )
            return True
        return False

    async def analyse_news_sentiment(
        self,
        symbol: str,
        base_asset: str,
        current_price: float,
        price_change_24h: float,
        volume_24h: float,
        indicators: dict[str, float],
        order_book_summary: dict[str, float],
        news_headlines: list[dict[str, str]],
    ) -> ClaudeSignalResponse | None:
        """Run the news sentiment analysis prompt."""
        rsi_signal = "neutral"
        rsi = indicators.get("rsi_14", 50)
        if rsi < 30:
            rsi_signal = "oversold"
        elif rsi > 70:
            rsi_signal = "overbought"

        atr = indicators.get("atr_14", 0)
        atr_pct = (atr / current_price * 100) if current_price > 0 else 0

        headlines_text = "\n".join(
            f"{i+1}. [{h.get('source', 'unknown')}] {h['title']}"
            for i, h in enumerate(news_headlines)
        )

        system_prompt = (
            "You are a quantitative crypto trading analyst.\n"
            "Your job is to determine whether a cryptocurrency is mispriced relative to breaking news, "
            "and whether there is a tradeable edge. You think in probabilities and expected value.\n"
            "You are precise, unemotional, and always justify your reasoning with specific evidence.\n"
            "You must respond ONLY with valid JSON matching the schema provided. No prose, no markdown."
        )

        user_prompt = f"""Analyse this cryptocurrency trading opportunity.

ASSET: {base_asset} ({symbol})
CURRENT PRICE: {current_price} USDT
24H CHANGE: {price_change_24h:.2f}%
24H VOLUME: ${volume_24h:,.0f} USDT

TECHNICAL CONTEXT:
RSI (14):       {rsi:.1f}   [{rsi_signal}]
MACD:           {indicators.get('macd', 0):.6f}  Signal: {indicators.get('macd_signal', 0):.6f}  Hist: {indicators.get('macd_hist', 0):+.6f}
Bollinger %B:   {indicators.get('bb_pct', 0):.2f}  (0=lower band, 1=upper band)
EMA 20:         {indicators.get('ema_20', 0):.4f}   EMA 50: {indicators.get('ema_50', 0):.4f}
ATR (14):       {atr:.4f}  ({atr_pct:.2f}% of price — current volatility)

ORDER BOOK (top 5 levels):
Best bid: {order_book_summary.get('best_bid', 0)} | Best ask: {order_book_summary.get('best_ask', 0)} | Spread: {order_book_summary.get('spread_pct', 0):.3f}%
Bid depth (top 5): ${order_book_summary.get('bid_depth', 0):,.0f} | Ask depth (top 5): ${order_book_summary.get('ask_depth', 0):,.0f}
Book imbalance: {order_book_summary.get('book_imbalance', 0):.2f}  (>1 = bid-heavy, <1 = ask-heavy)

RECENT NEWS (last 4 hours):
{headlines_text}

TASK:
1. Based on this news, has the market fully priced in the information? Or is there lag?
2. What direction (LONG or SHORT) offers the better expected value right now and why?
3. How confident are you?
4. Suggest a stop-loss and take-profit multiplier on ATR appropriate for the signal quality.

Respond with this exact JSON schema and nothing else:
{{
  "direction": "<LONG | SHORT | NONE>",
  "confidence": <float 0.0–1.0>,
  "edge_pct": <float>,
  "suggested_stop_atr_mult": <float>,
  "suggested_target_atr_mult": <float>,
  "reasoning": "<string, 4–6 sentences>",
  "key_catalysts": ["<string>"],
  "key_risks": ["<string>"]
}}"""

        return await self._call_claude(system_prompt, user_prompt)

    async def analyse_technical_confluence(
        self,
        symbol: str,
        current_price: float,
        timeframe: str,
        confluence_score: int,
        direction_label: str,
        indicators: dict[str, float],
        triggered_conditions: list[str],
    ) -> ClaudeSignalResponse | None:
        """Run the technical confluence analysis prompt."""
        system_prompt = (
            "You are a quantitative crypto trading analyst specialising in technical analysis.\n"
            "You must respond ONLY with valid JSON matching the schema provided. No prose, no markdown."
        )

        conditions_text = "\n".join(f"- {c}" for c in triggered_conditions)

        macd_hist = indicators.get("macd_hist", 0)
        macd_direction = "bullish" if macd_hist > 0 else "bearish"

        price = current_price
        ema20 = indicators.get("ema_20", 0)
        ema50 = indicators.get("ema_50", 0)
        price_vs_ema20 = "above" if price > ema20 else "below"
        ema20_vs_ema50 = "above" if ema20 > ema50 else "below"
        ema_relationship = f"EMA20 {'>' if ema20 > ema50 else '<'} EMA50"

        vol_sma = indicators.get("volume_sma_20", 1)
        vol_ratio = indicators.get("current_volume", 0) / vol_sma if vol_sma > 0 else 0

        user_prompt = f"""Analyse this technical setup.

ASSET: {symbol}
CURRENT PRICE: {current_price}
TIMEFRAME: {timeframe}
CONFLUENCE SCORE: {confluence_score}/6 ({direction_label})

INDICATORS:
RSI 14:        {indicators.get('rsi_14', 0):.1f}    (oversold < 30, overbought > 70)
MACD:          {indicators.get('macd', 0):.6f}  Signal: {indicators.get('macd_signal', 0):.6f}
MACD Hist:     {macd_hist:+.6f}  ({macd_direction})
Bollinger %B:  {indicators.get('bb_pct', 0):.2f}
EMA 20 vs 50:  {ema_relationship}  (price {price_vs_ema20} EMA20, EMA20 {ema20_vs_ema50} EMA50)
Volume:        {vol_ratio:.1f}× the 20-period average

TRIGGERED CONDITIONS:
{conditions_text}

TASK:
Rate the quality of this technical setup. Consider confluence strength, timeframe reliability,
and any conditions that conflict with the dominant signal.

Respond with this exact JSON schema and nothing else:
{{
  "direction": "<LONG | SHORT | NONE>",
  "confidence": <float 0.0–1.0>,
  "setup_quality": "<A | B | C>",
  "suggested_stop_atr_mult": <float>,
  "suggested_target_atr_mult": <float>,
  "reasoning": "<string, 3–5 sentences>",
  "conflicting_signals": ["<string>"],
  "supporting_signals": ["<string>"]
}}"""

        return await self._call_claude(system_prompt, user_prompt)

    async def analyse_volume_spike(
        self,
        symbol: str,
        current_price: float,
        volume_ratio: float,
        buy_pressure: float,
        book_imbalance: float,
        indicators: dict[str, float],
        recent_news_summary: str,
    ) -> ClaudeSignalResponse | None:
        """Run the volume spike analysis prompt."""
        system_prompt = (
            "You are a quantitative crypto trading analyst specialising in order flow analysis.\n"
            "You must respond ONLY with valid JSON matching the schema provided. No prose, no markdown."
        )

        user_prompt = f"""Analyse this unusual volume event.

ASSET: {symbol}
CURRENT PRICE: {current_price}
VOLUME RATIO: {volume_ratio:.1f}× the 20-period average
BUY PRESSURE: {buy_pressure:.2f} (>0.65 = dominant buying, <0.35 = dominant selling)
BOOK IMBALANCE: {book_imbalance:.2f} (>1.5 = bid wall, <0.67 = ask wall)

TECHNICAL CONTEXT:
RSI 14: {indicators.get('rsi_14', 0):.1f}
MACD Hist: {indicators.get('macd_hist', 0):+.6f}
ATR 14: {indicators.get('atr_14', 0):.4f}

RECENT NEWS CONTEXT:
{recent_news_summary}

TASK:
Does this volume pattern indicate informed accumulation/distribution, or is it noise?
What direction is most likely and how confident are you?

Respond with this exact JSON schema and nothing else:
{{
  "direction": "<LONG | SHORT | NONE>",
  "confidence": <float 0.0–1.0>,
  "edge_pct": <float>,
  "suggested_stop_atr_mult": <float>,
  "suggested_target_atr_mult": <float>,
  "reasoning": "<string, 4–6 sentences>",
  "key_catalysts": ["<string>"],
  "key_risks": ["<string>"]
}}"""

        return await self._call_claude(system_prompt, user_prompt)

    async def _call_claude(
        self, system_prompt: str, user_prompt: str
    ) -> ClaudeSignalResponse | None:
        """Send a prompt to Claude and parse the JSON response."""
        if self._is_rate_limited():
            return None

        try:
            response = await self.client.messages.create(
                model=self.MODEL,
                max_tokens=1024,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            self._hourly_calls += 1
            self._daily_calls += 1
            logger.debug(
                f"Claude call #{self._daily_calls} today "
                f"(#{self._hourly_calls} this hour)"
            )
            if not response.content or not response.content[0].text:
                logger.error("Claude returned empty response")
                return None
            text = response.content[0].text
            text = text.strip()
            logger.debug(f"Raw Claude response: {text}")
            data = json.loads(text)
            return ClaudeSignalResponse(**data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Claude JSON response: {e}")
            return None
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            return None
