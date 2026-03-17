"""Factory that returns the correct trader based on TRADE_MODE."""

from clients.exchange import ExchangeClient
from clients.redis import RedisClient
from clients.supabase import SupabaseClient
from config import Settings
from trading.base import BaseTrader
from trading.live_trader import LiveTrader
from trading.paper_trader import PaperTrader


def create_trader(
    settings: Settings,
    exchange: ExchangeClient,
    supabase: SupabaseClient,
    redis: RedisClient,
) -> BaseTrader:
    """Create the appropriate trader based on trade mode setting."""
    if settings.trade_mode == "live":
        return LiveTrader(settings, exchange, supabase, redis)
    return PaperTrader(settings, supabase, redis)
