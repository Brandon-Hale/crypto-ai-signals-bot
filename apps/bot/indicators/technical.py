"""Technical indicator calculations using the ta library."""

import pandas as pd
import ta.momentum
import ta.trend
import ta.volatility

from models.market import OHLCV, TechnicalIndicators


def compute_indicators(ohlcv: list[OHLCV]) -> TechnicalIndicators:
    """Compute all technical indicators from OHLCV data."""
    df = pd.DataFrame([c.model_dump() for c in ohlcv])

    return TechnicalIndicators(
        rsi_14=ta.momentum.RSIIndicator(df["close"], 14).rsi().iloc[-1],
        macd=ta.trend.MACD(df["close"]).macd().iloc[-1],
        macd_signal=ta.trend.MACD(df["close"]).macd_signal().iloc[-1],
        macd_hist=ta.trend.MACD(df["close"]).macd_diff().iloc[-1],
        bb_upper=ta.volatility.BollingerBands(df["close"]).bollinger_hband().iloc[-1],
        bb_lower=ta.volatility.BollingerBands(df["close"]).bollinger_lband().iloc[-1],
        bb_pct=ta.volatility.BollingerBands(df["close"]).bollinger_pband().iloc[-1],
        atr_14=ta.volatility.AverageTrueRange(
            df["high"], df["low"], df["close"]
        ).average_true_range().iloc[-1],
        ema_20=ta.trend.EMAIndicator(df["close"], 20).ema_indicator().iloc[-1],
        ema_50=ta.trend.EMAIndicator(df["close"], 50).ema_indicator().iloc[-1],
        volume_sma_20=df["volume"].rolling(20).mean().iloc[-1],
        current_volume=df["volume"].iloc[-1],
    )
