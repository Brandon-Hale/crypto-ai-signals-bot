"""Live trader — executes real orders via ccxt with full safety guards."""

import json
import math
from datetime import datetime, timezone

from loguru import logger

from clients.exchange import ExchangeClient
from clients.redis import RedisClient
from clients.supabase import SupabaseClient
from config import Settings
from models.market import Pair
from models.signal import Signal
from models.trade import TradeResult
from trading.base import BaseTrader


class LiveTrader(BaseTrader):
    """Live trading with exchange orders and full safety guards."""

    def __init__(
        self,
        settings: Settings,
        exchange: ExchangeClient,
        supabase: SupabaseClient,
        redis: RedisClient,
    ) -> None:
        self.settings = settings
        self.exchange = exchange
        self.supabase = supabase
        self.redis = redis

    @property
    def mode(self) -> str:
        return "live"

    async def _check_live_guards(
        self, signal: Signal, pair: Pair | None = None
    ) -> tuple[bool, str]:
        """Run all 8 safety guards. Returns (passed, reason)."""
        # 1. Explicit mode check
        if self.settings.trade_mode != "live":
            return False, "TRADE_MODE is not 'live'"

        # 2. Daily spend ceiling
        daily_spend_str = await self.redis.get("bot:live:daily_spend")
        daily_spend = float(daily_spend_str) if daily_spend_str else 0.0
        if daily_spend >= self.settings.bot_live_max_daily_spend:
            return False, f"Daily spend ceiling reached: ${daily_spend:.2f}"

        # 3. Minimum confidence
        if signal.confidence < self.settings.bot_live_min_confidence:
            return False, f"Confidence {signal.confidence:.2f} < {self.settings.bot_live_min_confidence}"

        # 4. Minimum risk/reward
        if signal.risk_reward < self.settings.bot_live_min_rr:
            return False, f"R:R {signal.risk_reward:.2f} < {self.settings.bot_live_min_rr}"

        # 5. Minimum volume
        if pair and pair.volume_24h and float(pair.volume_24h) < self.settings.bot_live_min_volume:
            return False, f"Volume ${pair.volume_24h} < ${self.settings.bot_live_min_volume}"

        # 6. Minimum volatility (ATR/price >= 0.5%)
        if pair and pair.atr_14 and pair.current_price:
            atr_pct = float(pair.atr_14) / float(pair.current_price)
            if atr_pct < 0.005:
                return False, f"Market too flat: ATR% = {atr_pct:.4f}"

        # 7. Max concurrent positions
        positions_str = await self.redis.get("bot:live:open_positions")
        positions = json.loads(positions_str) if positions_str else []
        if len(positions) >= self.settings.bot_live_max_positions:
            return False, f"Max positions reached: {len(positions)}"

        # 8. Sufficient balance
        balance = await self.exchange.fetch_balance()
        if balance:
            usdc = balance.get("USDC", {}).get("free", 0) or balance.get("USDT", {}).get("free", 0)
            if float(usdc) < self.settings.bot_live_trade_size:
                return False, f"Insufficient balance: ${usdc}"

        return True, "All guards passed"

    async def open_trade(self, signal: Signal) -> TradeResult:
        """Place a live limit order after passing all safety guards."""
        passed, reason = await self._check_live_guards(signal)
        if not passed:
            logger.warning(
                f"Live guard failed | reason={reason} | pair_id={signal.pair_id} | "
                f"direction={signal.direction} | confidence={signal.confidence:.2f} | rr={signal.risk_reward:.2f}"
            )
            raise ValueError(f"Safety guard failed: {reason}")

        # Resolve symbol — exchange calls need "BTC/USDT", not a UUID
        symbol = signal.symbol
        if not symbol:
            symbol = await self.redis.hget("pairs:id_to_symbol", signal.pair_id)
        if not symbol:
            raise ValueError(f"Could not resolve symbol for pair_id={signal.pair_id}")

        # Fetch current price
        ticker = await self.exchange.fetch_ticker(symbol)
        if not ticker:
            raise ValueError("Could not fetch current ticker")

        current_price = ticker["last"]
        if not current_price or current_price <= 0 or not math.isfinite(current_price):
            raise ValueError(f"Invalid current_price from ticker: {current_price}")

        slippage = self.settings.bot_live_slippage_tolerance

        if signal.direction == "LONG":
            limit_price = current_price * (1 + slippage)
            side = "buy"
        else:
            limit_price = current_price * (1 - slippage)
            side = "sell"

        amount = self.settings.bot_live_trade_size / current_price
        if amount <= 0 or not math.isfinite(amount):
            raise ValueError(f"Invalid order amount: {amount}")

        order = await self.exchange.create_limit_order(
            symbol, side, amount, limit_price
        )
        if not order:
            raise ValueError("Failed to place order on exchange")

        order_id = order["id"]

        trade_data = {
            "signal_id": signal.id,
            "pair_id": signal.pair_id,
            "mode": "live",
            "direction": signal.direction,
            "order_id": order_id,
            "exchange": self.settings.exchange_id,
            "entry_price": limit_price,
            "stop_price": signal.stop_price,
            "target_price": signal.target_price,
            "size_usd": self.settings.bot_live_trade_size,
            "size_base": amount,
            "status": "open",
        }
        result = await self.supabase.insert("trades", trade_data)

        # Update Redis tracking
        await self.redis.incrbyfloat(
            "bot:live:daily_spend", self.settings.bot_live_trade_size
        )

        positions_str = await self.redis.get("bot:live:open_positions")
        positions = json.loads(positions_str) if positions_str else []
        positions.append(order_id)
        await self.redis.set("bot:live:open_positions", json.dumps(positions))

        logger.info(
            f"Live order placed: {signal.direction} {signal.pair_id} "
            f"order_id={order_id} size=${self.settings.bot_live_trade_size}"
        )

        return TradeResult(
            id=result["id"] if result else None,
            signal_id=signal.id or "",
            pair_id=signal.pair_id,
            mode="live",
            direction=signal.direction,
            order_id=order_id,
            exchange=self.settings.exchange_id,
            entry_price=limit_price,
            stop_price=signal.stop_price,
            target_price=signal.target_price,
            size_usd=self.settings.bot_live_trade_size,
            size_base=amount,
            status="open",
        )

    async def close_trade(
        self, trade_id: str, exit_price: float, reason: str
    ) -> TradeResult:
        """Close a live trade — update records."""
        rows = await self.supabase.select("trades", filters={"id": trade_id})
        if not rows:
            raise ValueError(f"Trade {trade_id} not found")

        trade_data = rows[0]
        entry_price = float(trade_data["entry_price"])
        size_usd = float(trade_data["size_usd"])
        direction = trade_data["direction"]

        if entry_price <= 0 or not math.isfinite(entry_price):
            raise ValueError(f"Invalid entry_price: {entry_price}")
        if exit_price <= 0 or not math.isfinite(exit_price):
            raise ValueError(f"Invalid exit_price: {exit_price}")

        if direction == "LONG":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price
        pnl_usd = size_usd * pnl_pct

        if not math.isfinite(pnl_usd):
            raise ValueError(f"Calculated NaN/Inf P&L: {pnl_usd}")

        await self.supabase.update(
            "trades",
            trade_id,
            {
                "exit_price": exit_price,
                "pnl_usd": round(pnl_usd, 2),
                "pnl_pct": round(pnl_pct * 100, 4),
                "exit_reason": reason,
                "status": "closed",
                "closed_at": datetime.now(timezone.utc).isoformat(),
            },
        )

        # Remove from open positions in Redis
        order_id = trade_data.get("order_id")
        if order_id:
            positions_str = await self.redis.get("bot:live:open_positions")
            positions = json.loads(positions_str) if positions_str else []
            positions = [p for p in positions if p != order_id]
            await self.redis.set("bot:live:open_positions", json.dumps(positions))

        logger.info(
            f"Live trade closed: {direction} {trade_data.get('pair_id')} | "
            f"P&L: ${pnl_usd:+.2f} | reason={reason}"
        )

        return TradeResult(
            id=trade_id,
            signal_id=trade_data.get("signal_id", ""),
            pair_id=trade_data.get("pair_id", ""),
            mode="live",
            direction=direction,
            order_id=order_id,
            exchange=trade_data.get("exchange", "binance"),
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
        """Get all open live trades."""
        rows = await self.supabase.select(
            "trades", filters={"mode": "live", "status": "open"}
        )
        return [
            TradeResult(
                id=r["id"],
                signal_id=r["signal_id"],
                pair_id=r["pair_id"],
                mode="live",
                direction=r["direction"],
                order_id=r.get("order_id"),
                exchange=r.get("exchange", "binance"),
                entry_price=float(r["entry_price"]),
                stop_price=float(r["stop_price"]),
                target_price=float(r["target_price"]),
                size_usd=float(r["size_usd"]),
                size_base=float(r["size_base"]) if r.get("size_base") else None,
                status="open",
            )
            for r in rows
        ]

    async def check_and_close_by_price(
        self, current_prices: dict[str, float]
    ) -> list[TradeResult]:
        """Poll open live orders for fill status.

        Note: In production, OCO orders on the exchange handle exits.
        This is a fallback check.
        """
        open_trades = await self.get_open_trades()
        closed: list[TradeResult] = []

        for trade in open_trades:
            if not trade.order_id:
                continue

            # Resolve pair UUID to exchange symbol
            symbol = await self.redis.hget("pairs:id_to_symbol", trade.pair_id)
            if not symbol:
                logger.warning(f"Could not resolve symbol for pair_id={trade.pair_id}")
                continue

            order = await self.exchange.fetch_order(trade.order_id, symbol)
            if order and order.get("status") == "closed":
                fill_price = float(order.get("average", order.get("price", 0)))
                result = await self.close_trade(
                    trade.id or "", fill_price, "exchange_fill"
                )
                closed.append(result)

        return closed
