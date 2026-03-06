"""Deterministic reporting helpers for backtest results."""

from __future__ import annotations

from evengine.backtesting.backtest_types import BacktestResult


def compute_win_rate(result: BacktestResult) -> float:
    """Compute win rate from aggregate backtest counts."""

    if result.n_trades == 0:
        return 0.0
    return result.n_wins / result.n_trades


def compute_average_trade_pnl(result: BacktestResult) -> float:
    """Compute average PnL per executed trade."""

    if result.n_trades == 0:
        return 0.0
    return result.total_pnl / result.n_trades


def compute_max_drawdown(equity_curve: list[float]) -> float:
    """Compute deterministic maximum drawdown from an equity curve."""

    if not equity_curve:
        return 0.0

    peak: float = equity_curve[0]
    max_drawdown: float = 0.0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        if peak > 0.0:
            drawdown: float = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    return max_drawdown


def build_backtest_report(result: BacktestResult) -> dict:
    """Build a deterministic backtest report dictionary."""

    return {
        "win_rate": compute_win_rate(result),
        "average_trade_pnl": compute_average_trade_pnl(result),
        "max_drawdown": compute_max_drawdown(result.equity_curve),
        "final_balance": result.final_balance,
        "total_pnl": result.total_pnl,
        "n_trades": result.n_trades,
    }
