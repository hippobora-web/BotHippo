"""Deterministic ranking helpers for research strategy evaluations."""

from __future__ import annotations


def _selection_key(result: dict) -> tuple[float, float, float, str]:
    """Build a deterministic sort key for strategy selection."""

    strategy_id: str = str(result.get("strategy_config", {}).get("strategy_id", ""))
    return (
        float(result.get("total_pnl", 0.0)),
        float(result.get("win_rate", 0.0)),
        -float(result.get("max_drawdown", 0.0)),
        strategy_id,
    )


def select_best_strategies(results: list[dict], top_n: int = 5) -> list[dict]:
    """Select the best deterministic strategy evaluations."""

    ordered_results: list[dict] = sorted(results, key=_selection_key, reverse=True)
    return ordered_results[: max(0, top_n)]
