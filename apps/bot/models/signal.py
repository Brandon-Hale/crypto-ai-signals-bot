"""Signal models — AI-generated trading signals."""

from datetime import datetime

from pydantic import BaseModel


class ClaudeSignalResponse(BaseModel):
    """Parsed JSON response from Claude for signal generation."""

    direction: str  # "LONG" | "SHORT" | "NONE"
    confidence: float
    edge_pct: float | None = None
    suggested_stop_atr_mult: float | None = None
    suggested_target_atr_mult: float | None = None
    reasoning: str
    key_catalysts: list[str] = []
    key_risks: list[str] = []
    # Technical confluence specific
    setup_quality: str | None = None
    conflicting_signals: list[str] = []
    supporting_signals: list[str] = []


class Signal(BaseModel):
    """A trading signal persisted to Supabase."""

    id: str | None = None
    pair_id: str
    strategy: str  # "news_sentiment" | "technical_confluence" | "volume_spike"
    direction: str  # "LONG" | "SHORT"
    confidence: float
    entry_price: float
    target_price: float
    stop_price: float
    risk_reward: float
    edge_pct: float | None = None
    timeframe: str  # "1h" | "4h" | "1d"
    reasoning: str
    news_headlines: list[dict[str, str]] | None = None
    indicators: dict[str, float] | None = None
    signal_metadata: dict[str, float | str | list[str]] | None = None
    status: str = "open"  # "open" | "won" | "lost" | "stopped" | "expired" | "cancelled"
    created_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_price: float | None = None
