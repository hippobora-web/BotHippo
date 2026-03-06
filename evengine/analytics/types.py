"""Dataclasses for deterministic portfolio performance analytics."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PerformanceReport:
    """Aggregate deterministic performance metrics derived from portfolio PnL history."""

    total_pnl: float
    win_rate: float
    trades: int
    max_drawdown: float
    average_pnl: float
    pnl_variance: float
