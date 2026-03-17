"""Market data models — pairs, OHLCV candles, order books."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class Pair(BaseModel):
    """A trading pair being monitored."""

    id: str | None = None
    symbol: str  # e.g. "BTC/USDT"
    base_asset: str  # e.g. "BTC"
    quote_asset: str  # e.g. "USDT"
    category: str  # "large_cap" | "mid_cap" | "defi" | "layer1" | "layer2"
    current_price: Decimal | None = None
    price_change_24h: Decimal | None = None
    volume_24h: Decimal | None = None
    atr_14: Decimal | None = None
    is_active: bool = True
    last_updated: datetime | None = None


class OHLCV(BaseModel):
    """A single OHLCV candle."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OrderBookLevel(BaseModel):
    """A single price level in the order book."""

    price: float
    amount: float


class OrderBook(BaseModel):
    """Order book snapshot."""

    symbol: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    timestamp: datetime | None = None

    @property
    def best_bid(self) -> float:
        return self.bids[0].price if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        return self.asks[0].price if self.asks else 0.0

    @property
    def spread_pct(self) -> float:
        if self.best_bid == 0:
            return 0.0
        return ((self.best_ask - self.best_bid) / self.best_bid) * 100

    @property
    def bid_depth_top5(self) -> float:
        return sum(level.price * level.amount for level in self.bids[:5])

    @property
    def ask_depth_top5(self) -> float:
        return sum(level.price * level.amount for level in self.asks[:5])

    @property
    def book_imbalance(self) -> float:
        ask_depth = self.ask_depth_top5
        if ask_depth == 0:
            return 0.0
        return self.bid_depth_top5 / ask_depth


class TechnicalIndicators(BaseModel):
    """Computed technical indicator values for a pair at a point in time."""

    rsi_14: float
    macd: float
    macd_signal: float
    macd_hist: float
    bb_upper: float
    bb_lower: float
    bb_pct: float
    atr_14: float
    ema_20: float
    ema_50: float
    volume_sma_20: float
    current_volume: float
