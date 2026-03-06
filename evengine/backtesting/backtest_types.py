"""Dataclasses for deterministic backtesting inputs and outputs."""

from __future__ import annotations

from dataclasses import dataclass, field

from evengine.strategy.strategy_types import StrategyInput


@dataclass
class BacktestInput:
    """Input payload for running a deterministic strategy backtest."""

    rows: list[StrategyInput] = field(default_factory=list)
    outcomes: list[bool] = field(default_factory=list)
    initial_balance: float = 0.0


@dataclass
class BacktestResult:
    """Aggregate deterministic result of a backtest run."""

    final_balance: float
    total_pnl: float
    n_trades: int
    n_wins: int
    n_losses: int
    equity_curve: list[float] = field(default_factory=list)
