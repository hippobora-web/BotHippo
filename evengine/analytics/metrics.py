"""Deterministic portfolio performance metric helpers."""

from __future__ import annotations

from evengine.analytics.types import PerformanceReport


def compute_average_pnl(pnl_history: list[float]) -> float:
    """Compute the average PnL across a history of trade results."""

    if not pnl_history:
        return 0.0
    return sum(pnl_history) / len(pnl_history)



def compute_pnl_variance(pnl_history: list[float]) -> float:
    """Compute the deterministic population variance of trade PnL."""

    if not pnl_history:
        return 0.0
    mean_pnl: float = compute_average_pnl(pnl_history)
    return sum((pnl - mean_pnl) ** 2 for pnl in pnl_history) / len(pnl_history)



def _compute_max_drawdown(pnl_history: list[float]) -> float:
    """Compute maximum drawdown from cumulative PnL."""

    if not pnl_history:
        return 0.0

    equity: float = 0.0
    peak: float = 0.0
    max_drawdown: float = 0.0

    for pnl in pnl_history:
        equity += pnl
        if equity > peak:
            peak = equity
        drawdown: float = peak - equity
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    return max_drawdown



def build_performance_report(
    pnl_history: list[float],
    wins: int,
    trades: int,
) -> PerformanceReport:
    """Build a deterministic performance report from portfolio trade outcomes."""

    total_pnl: float = sum(pnl_history)
    win_rate: float = wins / trades if trades > 0 else 0.0
    return PerformanceReport(
        total_pnl=total_pnl,
        win_rate=win_rate,
        trades=trades,
        max_drawdown=_compute_max_drawdown(pnl_history),
        average_pnl=compute_average_pnl(pnl_history),
        pnl_variance=compute_pnl_variance(pnl_history),
    )
