"""Paper trader — simulates trades by logging to Supabase only."""

from datetime import datetime, timezone

from loguru import logger

from clients.redis import RedisClient
from clients.supabase import SupabaseClient
from config import Settings
from models.signal import Signal
from models.trade import TradeResult
from trading.base import BaseTrader


class PaperTrader(BaseTrader):
    """Paper trading implementation — no real orders, Supabase-only."""

    def __init__(
        self, settings: Settings, supabase: SupabaseClient, redis: RedisClient
    ) -> None:
        self.settings = settings
        self.supabase = supabase
        self.redis = redis
        self.trade_size = settings.bot_paper_trade_size

    @property
    def mode(self) -> str:
        return "paper"

    async def open_trade(self, signal: Signal) -> TradeResult:
        """Open a paper trade at current market price."""
        # Use live price from Redis, not signal price (avoids look-ahead bias)
        price_str = await self.redis.hget("pairs:prices", signal.pair_id)
        entry_price = float(price_str) if price_str else signal.entry_price

        trade_data = {
            "signal_id": signal.id,
            "pair_id": signal.pair_id,
            "mode": "paper",
            "direction": signal.direction,
            "exchange": "binance",
            "entry_price": entry_price,
            "stop_price": signal.stop_price,
            "target_price": signal.target_price,
            "size_usd": self.trade_size,
            "status": "open",
        }

        result = await self.supabase.insert("trades", trade_data)
        trade_id = result["id"] if result else None

        trade = TradeResult(
            id=trade_id,
            signal_id=signal.id or "",
            pair_id=signal.pair_id,
            mode="paper",
            direction=signal.direction,
            entry_price=entry_price,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            size_usd=self.trade_size,
            status="open",
        )

        logger.info(
            f"Paper trade opened: {signal.direction} {signal.pair_id} "
            f"@ {entry_price} | size=${self.trade_size}"
        )
        return trade

    async def close_trade(
        self, trade_id: str, exit_price: float, reason: str
    ) -> TradeResult:
        """Close a paper trade and calculate P&L."""
        rows = await self.supabase.select("trades", filters={"id": trade_id})
        if not rows:
            raise ValueError(f"Trade {trade_id} not found")

        trade_data = rows[0]
        entry_price = float(trade_data["entry_price"])
        size_usd = float(trade_data["size_usd"])
        direction = trade_data["direction"]

        if direction == "LONG":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price

        pnl_usd = size_usd * pnl_pct

        update = {
            "exit_price": exit_price,
            "pnl_usd": round(pnl_usd, 2),
            "pnl_pct": round(pnl_pct * 100, 4),
            "exit_reason": reason,
            "status": "closed",
            "closed_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.supabase.update("trades", trade_id, update)

        # Update signal status
        signal_id = trade_data.get("signal_id")
        if signal_id:
            signal_status = "won" if pnl_usd > 0 else "lost"
            if reason == "stopped":
                signal_status = "stopped"
            elif reason == "expired":
                signal_status = "expired"
            await self.supabase.update(
                "signals",
                signal_id,
                {
                    "status": signal_status,
                    "resolved_at": datetime.now(timezone.utc).isoformat(),
                    "resolved_price": exit_price,
                },
            )

        logger.info(
            f"Paper trade closed: {direction} {trade_data.get('pair_id')} | "
            f"P&L: ${pnl_usd:+.2f} ({pnl_pct:+.2f}%) | reason={reason}"
        )

        return TradeResult(
            id=trade_id,
            signal_id=signal_id or "",
            pair_id=trade_data.get("pair_id", ""),
            mode="paper",
            direction=direction,
            entry_price=entry_price,
            exit_price=exit_price,
            stop_price=float(trade_data["stop_price"]),
            target_price=float(trade_data["target_price"]),
            size_usd=size_usd,
            pnl_usd=round(pnl_usd, 2),
            pnl_pct=round(pnl_pct * 100, 4),
            exit_reason=reason,
            status="closed",
        )

    async def get_open_trades(self) -> list[TradeResult]:
        """Get all open paper trades."""
        rows = await self.supabase.select(
            "trades", filters={"mode": "paper", "status": "open"}
        )
        return [
            TradeResult(
                id=r["id"],
                signal_id=r["signal_id"],
                pair_id=r["pair_id"],
                mode="paper",
                direction=r["direction"],
                entry_price=float(r["entry_price"]),
                stop_price=float(r["stop_price"]),
                target_price=float(r["target_price"]),
                size_usd=float(r["size_usd"]),
                status="open",
            )
            for r in rows
        ]

    async def check_and_close_by_price(
        self, current_prices: dict[str, float]
    ) -> list[TradeResult]:
        """Check open trades against current prices, close hits."""
        open_trades = await self.get_open_trades()
        closed: list[TradeResult] = []

        for trade in open_trades:
            price = current_prices.get(trade.pair_id)
            if price is None:
                continue

            if trade.direction == "LONG":
                if price >= trade.target_price:
                    result = await self.close_trade(
                        trade.id or "", trade.target_price, "target_hit"
                    )
                    closed.append(result)
                elif price <= trade.stop_price:
                    result = await self.close_trade(
                        trade.id or "", trade.stop_price, "stop_hit"
                    )
                    closed.append(result)
            else:  # SHORT
                if price <= trade.target_price:
                    result = await self.close_trade(
                        trade.id or "", trade.target_price, "target_hit"
                    )
                    closed.append(result)
                elif price >= trade.stop_price:
                    result = await self.close_trade(
                        trade.id or "", trade.stop_price, "stop_hit"
                    )
                    closed.append(result)

        return closed
