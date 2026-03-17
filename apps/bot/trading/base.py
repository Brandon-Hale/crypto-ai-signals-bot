"""Abstract base trader — interface for paper and live implementations."""

from abc import ABC, abstractmethod

from models.signal import Signal
from models.trade import TradeResult


class BaseTrader(ABC):
    """All trade execution must go through this interface."""

    @abstractmethod
    async def open_trade(self, signal: Signal) -> TradeResult:
        ...

    @abstractmethod
    async def close_trade(
        self, trade_id: str, exit_price: float, reason: str
    ) -> TradeResult:
        ...

    @abstractmethod
    async def get_open_trades(self) -> list[TradeResult]:
        ...

    @abstractmethod
    async def check_and_close_by_price(
        self, current_prices: dict[str, float]
    ) -> list[TradeResult]:
        """Check all open trades — close any that have hit stop or target."""
        ...

    @property
    @abstractmethod
    def mode(self) -> str:
        ...
