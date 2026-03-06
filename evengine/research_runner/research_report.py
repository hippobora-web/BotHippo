"""Deterministic reporting helpers for orchestrated research runs."""

from __future__ import annotations


def _average_total_pnl(results: list[dict]) -> float:
    """Compute average total pnl across evaluated strategies."""

    if not results:
        return 0.0
    return sum(float(result.get("total_pnl", 0.0)) for result in results) / len(results)


def _best_win_rate(best_strategies: list[dict]) -> float:
    """Return the best win rate among selected strategies."""

    if not best_strategies:
        return 0.0
    return max(float(result.get("win_rate", 0.0)) for result in best_strategies)


def build_research_report(research_result: dict) -> dict:
    """Build a deterministic research summary report."""

    evaluation_results: list[dict] = list(research_result.get("evaluation_results", []))
    best_strategies: list[dict] = list(research_result.get("best_strategies", []))
    best_strategy: dict = best_strategies[0] if best_strategies else {}
    return {
        "n_strategies_tested": int(research_result.get("strategies_tested", 0)),
        "best_strategy": best_strategy,
        "top_strategies": best_strategies,
        "summary_metrics": {
            "n_best_strategies": len(best_strategies),
            "average_total_pnl": _average_total_pnl(evaluation_results),
            "best_total_pnl": float(best_strategy.get("total_pnl", 0.0)) if best_strategy else 0.0,
            "best_win_rate": _best_win_rate(best_strategies),
        },
    }
