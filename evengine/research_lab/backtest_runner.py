"""Deterministic paper-trading backtest runner for the WINA research lab."""

from __future__ import annotations

import math

from evengine.research_lab.schemas import BacktestMetrics, StrategySpec


def compute_drawdown(equity_curve: list[float]) -> float:
    """Compute maximum drawdown from an equity curve."""

    if not equity_curve:
        return 0.0

    peak: float = equity_curve[0]
    max_drawdown: float = 0.0
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        if peak > 0:
            drawdown: float = (peak - equity) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
    return max_drawdown


def compute_volatility(returns: list[float]) -> float:
    """Compute deterministic population standard deviation of returns."""

    if not returns:
        return 0.0

    mean_return: float = sum(returns) / len(returns)
    variance: float = sum((value - mean_return) ** 2 for value in returns) / len(returns)
    return math.sqrt(variance)


def _min_edge_from_strategy(strategy_spec: StrategySpec) -> float:
    """Extract minimum edge gate from strategy parameters with safe fallback."""

    raw_value = strategy_spec.params.get("min_edge", 0.0)
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return 0.0


def _profit_for_row(row: dict) -> float:
    """Compute 1-unit paper-trading profit for a settled market row."""

    odds: float = float(row["odds"])
    result: int = int(row["result"])
    if result == 1:
        return odds - 1.0
    return -1.0


def _stability_score(roi: float, max_drawdown: float, volatility: float) -> float:
    """Compute a bounded stability score from outcome smoothness metrics."""

    score: float = 1.0 + min(roi, 1.0) - max_drawdown - volatility
    return max(0.0, min(1.0, score))


def simulate_strategy(
    strategy_spec: StrategySpec,
    market_rows: list[dict],
) -> BacktestMetrics:
    """Run a deterministic 1-unit paper-trading simulation over market rows."""

    min_edge: float = _min_edge_from_strategy(strategy_spec)
    selected_rows: list[dict] = []
    edges: list[float] = []
    returns: list[float] = []
    equity_curve: list[float] = []
    cumulative_profit: float = 0.0
    wins: int = 0

    for row in market_rows:
        implied_prob: float = float(row["implied_prob"])
        model_prob: float = float(row["model_prob"])
        edge: float = model_prob - implied_prob
        if edge < min_edge:
            continue

        profit: float = _profit_for_row(row)
        cumulative_profit += profit
        selected_rows.append(row)
        edges.append(edge)
        returns.append(profit)
        equity_curve.append(1.0 + cumulative_profit)
        if int(row["result"]) == 1:
            wins += 1

    sample_size: int = len(selected_rows)
    if sample_size == 0:
        return BacktestMetrics(
            sample_size=0,
            roi=0.0,
            hit_rate=0.0,
            avg_edge=0.0,
            max_drawdown=0.0,
            volatility=0.0,
            stability_score=0.0,
        )

    total_profit: float = sum(returns)
    roi: float = total_profit / sample_size
    hit_rate: float = wins / sample_size
    avg_edge: float = sum(edges) / sample_size
    max_drawdown: float = compute_drawdown(equity_curve)
    volatility: float = compute_volatility(returns)
    stability_score: float = _stability_score(roi, max_drawdown, volatility)

    return BacktestMetrics(
        sample_size=sample_size,
        roi=roi,
        hit_rate=hit_rate,
        avg_edge=avg_edge,
        max_drawdown=max_drawdown,
        volatility=volatility,
        stability_score=stability_score,
    )
