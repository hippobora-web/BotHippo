"""Deterministic strategy evaluation helpers built on the backtesting engine."""

from __future__ import annotations

from evengine.backtesting.backtest_engine import run_backtest
from evengine.backtesting.backtest_report import build_backtest_report
from evengine.strategy.strategy_types import StrategyInput


def _row_edge(row: StrategyInput) -> float | None:
    """Compute a simple per-row edge when both probabilities are available."""

    if row.model_probability is None or row.market_implied_probability is None:
        return None
    return row.model_probability - row.market_implied_probability


def _passes_strategy_filters(row: StrategyInput, strategy_config: dict) -> bool:
    """Return whether a dataset row passes the deterministic strategy filters."""

    edge: float | None = _row_edge(row)
    if edge is None or edge < float(strategy_config.get("min_edge_threshold", 0.0)):
        return False
    if row.confidence is None or row.confidence < float(strategy_config.get("min_confidence", 0.0)):
        return False
    if row.liquidity_score is None or row.liquidity_score < float(strategy_config.get("min_liquidity", 0.0)):
        return False
    return True


def _apply_strategy_config(dataset: list[StrategyInput], strategy_config: dict) -> list[StrategyInput]:
    """Adapt dataset rows to an existing pipeline by neutralizing rows that fail filters."""

    adjusted_rows: list[StrategyInput] = []
    for row in dataset:
        if _passes_strategy_filters(row, strategy_config):
            adjusted_rows.append(row)
            continue
        adjusted_rows.append(
            StrategyInput(
                asset_class=row.asset_class,
                market_implied_probability=row.market_implied_probability,
                model_probability=row.market_implied_probability,
                confidence=row.confidence,
                liquidity_score=row.liquidity_score,
                current_exposure=row.current_exposure,
            )
        )
    return adjusted_rows


def evaluate_strategy(
    dataset: list[StrategyInput],
    outcomes: list[bool],
    strategy_config: dict,
) -> dict:
    """Evaluate one deterministic research strategy configuration with backtesting."""

    adjusted_dataset: list[StrategyInput] = _apply_strategy_config(dataset, strategy_config)
    result = run_backtest(adjusted_dataset, outcomes, initial_balance=0.0)
    report: dict = build_backtest_report(result)
    return {
        "strategy_config": strategy_config,
        "final_balance": result.final_balance,
        "total_pnl": result.total_pnl,
        "n_trades": result.n_trades,
        "n_wins": result.n_wins,
        "n_losses": result.n_losses,
        "equity_curve": result.equity_curve,
        **report,
    }
