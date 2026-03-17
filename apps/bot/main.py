"""Entry point — initializes all clients and starts the strategy scheduler."""

import asyncio
import signal
import sys

from loguru import logger

from clients.claude import ClaudeClient
from clients.exchange import ExchangeClient
from clients.news import NewsClient
from clients.redis import RedisClient, redis_client
from clients.supabase import SupabaseClient, supabase_client
from config import settings
from scheduler import StrategyScheduler
from trader_factory import create_trader


async def main() -> None:
    """Initialize clients and start the bot."""
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)
    logger.info(f"Starting crypto signal bot — mode={settings.trade_mode}")

    # Initialize clients
    redis = redis_client
    supabase = supabase_client
    await supabase.init()

    exchange = ExchangeClient(settings, redis)
    claude = ClaudeClient()
    news = NewsClient(settings, redis)

    # Create trader based on mode
    trader = create_trader(settings, exchange, supabase, redis)
    logger.info(f"Trader initialized: {trader.mode} mode")

    # Start scheduler
    scheduler = StrategyScheduler(
        settings, exchange, claude, news, redis, supabase, trader
    )
    scheduler.start()

    # Graceful shutdown handler
    stop_event = asyncio.Event()

    def handle_shutdown(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    # Write initial status
    await redis.set("bot:status", "idle")
    await redis.set("bot:trade_mode", trader.mode)

    # Wait for shutdown signal
    await stop_event.wait()

    # Cleanup
    logger.info("Shutting down...")
    scheduler.stop()
    await exchange.close()
    await news.close()
    await redis.set("bot:status", "stopped")
    logger.info("Bot stopped cleanly")


if __name__ == "__main__":
    asyncio.run(main())
