"""Signal models — AI-generated trading signals."""

from datetime import datetime

from pydantic import BaseModel, field_validator


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
    symbol: str | None = None  # e.g. "BTC/USDT" — in-memory only, not persisted to DB
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
    status: str = "open"
    created_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_price: float | None = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v: str) -> str:
        if v not in ("LONG", "SHORT"):
            raise ValueError(f"direction must be 'LONG' or 'SHORT', got '{v}'")
        return v

    @field_validator("strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        valid = {"news_sentiment", "technical_confluence", "volume_spike"}
        if v not in valid:
            raise ValueError(f"strategy must be one of {valid}, got '{v}'")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if v < 0.0 or v > 1.0:
            raise ValueError(f"confidence must be 0.0-1.0, got {v}")
        return v

    @field_validator("entry_price", "target_price", "stop_price")
    @classmethod
    def validate_positive_price(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"price must be positive, got {v}")
        return v

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        if v not in ("1h", "4h", "1d"):
            raise ValueError(f"timeframe must be '1h', '4h', or '1d', got '{v}'")
        return v
