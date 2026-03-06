"""In-memory deterministic paper portfolio accounting."""

from __future__ import annotations

from evengine.paper_trading.trade_types import TradeResult


class PaperPortfolio:
    """Simple deterministic paper portfolio tracking balance and trade history."""

    def __init__(self, starting_balance: float = 0.0) -> None:
        """Initialize the paper portfolio with an optional starting balance."""

        self.starting_balance: float = starting_balance
        self.balance: float = starting_balance
        self.trades: list[TradeResult] = []
        self.equity_curve: list[float] = []

    def apply_trade(self, result: TradeResult) -> None:
        """Apply one simulated trade result to the portfolio state."""

        self.trades.append(result)
        self.balance += result.pnl
        self.equity_curve.append(self.balance)

    def compute_total_pnl(self) -> float:
        """Return the total realized paper-trading PnL."""

        return sum(trade.pnl for trade in self.trades)

    def compute_equity_curve(self) -> list[float]:
        """Recompute and return the deterministic equity curve from trade history."""

        balance: float = self.starting_balance
        equity_curve: list[float] = []
        for trade in self.trades:
            balance += trade.pnl
            equity_curve.append(balance)
        self.equity_curve = equity_curve
        return list(self.equity_curve)
