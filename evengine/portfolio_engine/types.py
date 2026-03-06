"""Dataclasses for deterministic portfolio aggregation and metrics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PortfolioState:
    """Current deterministic portfolio state built from simulated trade PnL events."""

    balance: float
    trades: int
    wins: int
    losses: int
    pnl_history: list[float] = field(default_factory=list)


@dataclass
class PortfolioMetrics:
    """Aggregate deterministic portfolio metrics computed from portfolio state."""

    total_pnl: float
    roi: float
    win_rate: float
    max_drawdown: float
