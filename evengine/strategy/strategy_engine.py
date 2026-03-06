"""Deterministic strategy engine wiring dataset-style rows into the decision pipeline."""

from __future__ import annotations

from evengine.pipeline.decision_pipeline import run_decision_pipeline
from evengine.pipeline.decision_types import DecisionInput
from evengine.strategy.strategy_types import StrategyDecision, StrategyInput


def run_strategy_row(inp: StrategyInput) -> StrategyDecision:
    """Run one strategy input row through the generic decision pipeline."""

    decision_output = run_decision_pipeline(
        DecisionInput(
            asset_class=inp.asset_class,
            market_implied_probability=inp.market_implied_probability,
            model_probability=inp.model_probability,
            confidence=inp.confidence,
            liquidity_score=inp.liquidity_score,
            current_exposure=inp.current_exposure,
        )
    )
    return StrategyDecision(
        asset_class=decision_output.asset_class,
        decision=decision_output.risk_verdict,
        approved=decision_output.approved,
        size=decision_output.recommended_size,
        edge=decision_output.edge,
        reasons=decision_output.reasons,
    )


def run_strategy_dataset(rows: list[StrategyInput]) -> list[StrategyDecision]:
    """Run a batch of strategy inputs deterministically in order."""

    return [run_strategy_row(row) for row in rows]
