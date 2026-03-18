"""Technical indicator calculations using the ta library."""

import pandas as pd
import ta.momentum
import ta.trend
import ta.volatility

from models.market import OHLCV, TechnicalIndicators


def compute_indicators(ohlcv: list[OHLCV]) -> TechnicalIndicators:
    """Compute all technical indicators from OHLCV data."""
    df = pd.DataFrame([c.model_dump() for c in ohlcv])

    close = df["close"]
    macd_ind = ta.trend.MACD(close)
    bb_ind = ta.volatility.BollingerBands(close)

    return TechnicalIndicators(
        rsi_14=ta.momentum.RSIIndicator(close, 14).rsi().iloc[-1],
        macd=macd_ind.macd().iloc[-1],
        macd_signal=macd_ind.macd_signal().iloc[-1],
        macd_hist=macd_ind.macd_diff().iloc[-1],
        bb_upper=bb_ind.bollinger_hband().iloc[-1],
        bb_lower=bb_ind.bollinger_lband().iloc[-1],
        bb_pct=bb_ind.bollinger_pband().iloc[-1],
        atr_14=ta.volatility.AverageTrueRange(
            df["high"], df["low"], close
        ).average_true_range().iloc[-1],
        ema_20=ta.trend.EMAIndicator(close, 20).ema_indicator().iloc[-1],
        ema_50=ta.trend.EMAIndicator(close, 50).ema_indicator().iloc[-1],
        volume_sma_20=df["volume"].rolling(20).mean().iloc[-1],
        current_volume=df["volume"].iloc[-1],
    )
