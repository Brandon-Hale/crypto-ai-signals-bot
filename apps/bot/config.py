"""Bot configuration via pydantic-settings. All values loaded from environment variables."""

from pydantic import BaseModel, Field
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
    bot_paper_trade_size: float = 200.0
    bot_min_confidence: float = 0.65
    bot_min_rr: float = 1.5

    # Live trading
    bot_live_trade_size: float = 10.0
    bot_live_min_confidence: float = 0.75
    bot_live_min_rr: float = 1.8
    bot_live_min_volume: float = 5_000_000.0
    bot_live_max_positions: int = 3
    bot_live_max_daily_spend: float = 50.0
    bot_live_order_ttl_minutes: int = 15
    bot_live_slippage_tolerance: float = 0.002

    # Strategy
    bot_max_pairs: int = 30
    bot_strategy_interval_minutes: int = 5
    bot_default_stop_atr_mult: float = 1.5
    bot_default_target_atr_mult: float = 2.5
    log_level: str = "INFO"

    # Cost controls
    bot_max_claude_calls_per_hour: int = 60      # hard cap on Claude API calls per hour
    bot_max_claude_calls_per_day: int = 500       # hard cap on Claude API calls per day
    bot_max_redis_commands_per_loop: int = 500    # circuit breaker per strategy loop

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
