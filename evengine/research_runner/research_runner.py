"""Deterministic orchestration helpers for the full research pipeline."""

from __future__ import annotations

from evengine.research.strategy_evaluator import evaluate_strategy
from evengine.research.strategy_generator import generate_strategies
from evengine.research.strategy_selector import select_best_strategies
from evengine.strategy.strategy_types import StrategyInput


def run_research(dataset: list[StrategyInput], outcomes: list[bool]) -> dict:
    """Run the full deterministic research flow over a dataset and outcomes."""

    strategies: list[dict] = generate_strategies()
    evaluation_results: list[dict] = [
        evaluate_strategy(dataset, outcomes, strategy_config)
        for strategy_config in strategies
    ]
    best_strategies: list[dict] = select_best_strategies(evaluation_results)
    return {
        "strategies_tested": len(strategies),
        "best_strategies": best_strategies,
        "evaluation_results": evaluation_results,
    }
