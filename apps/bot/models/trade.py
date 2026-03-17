"""Trade models — paper and live trade records."""

from datetime import datetime

from pydantic import BaseModel


class TradeResult(BaseModel):
    """Result of opening or closing a trade."""

    id: str | None = None
    signal_id: str
    pair_id: str
    mode: str  # "paper" | "live"
    direction: str  # "LONG" | "SHORT"
    order_id: str | None = None
    exchange: str = "binance"
    entry_price: float
    exit_price: float | None = None
    stop_price: float
    target_price: float
    size_usd: float
    size_base: float | None = None
    pnl_usd: float | None = None
    pnl_pct: float | None = None
    fees_usd: float = 0.0
    exit_reason: str | None = None  # "target_hit" | "stop_hit" | "expired" | "manual"
    status: str = "open"  # "open" | "closed" | "cancelled"
    opened_at: datetime | None = None
    closed_at: datetime | None = None
