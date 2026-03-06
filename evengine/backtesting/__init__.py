"""Public exports for deterministic backtesting helpers."""

from evengine.backtesting.backtest_engine import run_backtest
from evengine.backtesting.backtest_report import (
    build_backtest_report,
    compute_average_trade_pnl,
    compute_max_drawdown,
    compute_win_rate,
)
from evengine.backtesting.backtest_types import BacktestInput, BacktestResult

__all__ = [
    "BacktestInput",
    "BacktestResult",
    "build_backtest_report",
    "compute_average_trade_pnl",
    "compute_max_drawdown",
    "compute_win_rate",
    "run_backtest",
]
