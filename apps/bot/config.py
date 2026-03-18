"""Bot configuration via pydantic-settings. All values loaded from environment variables."""

from loguru import logger
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — loaded from environment variables."""

    # Core APIs
    anthropic_api_key: str
    supabase_url: str = Field(alias="NEXT_PUBLIC_SUPABASE_URL")
    supabase_service_key: str
    upstash_redis_rest_url: str
    upstash_redis_rest_token: str
    cryptopanic_api_key: str = ""
    news_api_key: str = ""

    # Exchange
    exchange_id: str = "binance"
    exchange_api_key: str = ""
    exchange_api_secret: str = ""
    exchange_market_type: str = "spot"

    # Trade mode
    trade_mode: str = "paper"  # "paper" | "live"

    # Paper trading
    bot_paper_trade_size: float = Field(200.0, ge=1.0, le=50000.0)
    bot_min_confidence: float = Field(0.65, ge=0.0, le=1.0)
    bot_min_rr: float = Field(1.0, ge=0.1, le=10.0)  # TEMP: lowered for testing (normal: 1.5)

    # Live trading
    bot_live_trade_size: float = Field(10.0, ge=1.0, le=5000.0)
    bot_live_min_confidence: float = Field(0.75, ge=0.0, le=1.0)
    bot_live_min_rr: float = Field(1.8, ge=0.1, le=10.0)
    bot_live_min_volume: float = 5_000_000.0
    bot_live_max_positions: int = Field(3, ge=1, le=20)
    bot_live_max_daily_spend: float = Field(50.0, ge=1.0, le=10000.0)
    bot_live_order_ttl_minutes: int = Field(15, ge=1, le=120)
    bot_live_slippage_tolerance: float = Field(0.002, ge=0.0001, le=0.05)

    # Strategy
    bot_max_pairs: int = Field(30, ge=1, le=100)
    bot_strategy_interval_minutes: int = Field(5, ge=1, le=60)
    bot_default_stop_atr_mult: float = Field(0.3, ge=0.1, le=10.0)  # TEMP: tightened for testing (normal: 1.5)
    bot_default_target_atr_mult: float = Field(0.5, ge=0.1, le=20.0)  # TEMP: tightened for testing (normal: 2.5)

    # Claude model
    claude_model: str = "claude-sonnet-4-20250514"

    log_level: str = "INFO"

    # Cost controls
    bot_max_claude_calls_per_hour: int = Field(200, ge=1, le=1000)
    bot_max_claude_calls_per_day: int = Field(2000, ge=1, le=10000)
    bot_max_redis_commands_per_loop: int = Field(1500, ge=100, le=10000)

    @field_validator("trade_mode")
    @classmethod
    def validate_trade_mode(cls, v: str) -> str:
        if v not in ("paper", "live"):
            raise ValueError(f"trade_mode must be 'paper' or 'live', got '{v}'")
        return v

    @field_validator("exchange_id")
    @classmethod
    def validate_exchange_id(cls, v: str) -> str:
        allowed = {"binance", "bybit", "okx", "kraken", "coinbase"}
        if v not in allowed:
            raise ValueError(f"exchange_id must be one of {allowed}, got '{v}'")
        return v

    @model_validator(mode="after")
    def warn_temp_values(self) -> "Settings":
        """Log warnings for values that deviate from production defaults."""
        if self.bot_min_rr < 1.5:
            logger.warning(
                f"bot_min_rr={self.bot_min_rr} is below production default (1.5) — testing mode?"
            )
        if self.bot_default_stop_atr_mult < 1.0:
            logger.warning(
                f"bot_default_stop_atr_mult={self.bot_default_stop_atr_mult} is below production default (1.5) — tight stops active"
            )
        if self.bot_default_target_atr_mult < 2.0:
            logger.warning(
                f"bot_default_target_atr_mult={self.bot_default_target_atr_mult} is below production default (2.5) — tight targets active"
            )
        if self.trade_mode == "live" and not self.exchange_api_key:
            raise ValueError("exchange_api_key is required when trade_mode is 'live'")
        if self.trade_mode == "live" and not self.exchange_api_secret:
            raise ValueError("exchange_api_secret is required when trade_mode is 'live'")
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
