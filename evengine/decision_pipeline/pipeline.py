"""Deterministic orchestration layer for the shared WINA decision core."""

from __future__ import annotations

from evengine.core import (
    DecisionInput,
    build_edge_signal,
    build_fair_value_estimate,
    build_risk_decision,
    build_trade_intent,
    decision_input_from_research_row,
)
from evengine.decision_pipeline.types import PipelineConfig, PipelineResult


def run_decision_pipeline(
    decision_input: DecisionInput,
    *,
    config: PipelineConfig | None = None,
) -> PipelineResult:
    """Run the shared deterministic decision pipeline for one decision input."""

    effective_config: PipelineConfig = PipelineConfig() if config is None else config
    fair_value = build_fair_value_estimate(decision_input)
    edge_signal = build_edge_signal(
        fair_value,
        min_edge=effective_config.min_edge,
        min_confidence=effective_config.min_confidence,
        min_liquidity=effective_config.min_liquidity,
    )
    risk_decision = build_risk_decision(
        edge_signal,
        max_position_size=effective_config.max_position_size,
        max_total_exposure=effective_config.max_total_exposure,
        current_exposure=0.0 if decision_input.current_exposure is None else decision_input.current_exposure,
    )
    trade_intent = build_trade_intent(
        signal=edge_signal,
        risk_decision=risk_decision,
    )
    return PipelineResult(
        decision_input=decision_input,
        fair_value=fair_value,
        edge_signal=edge_signal,
        risk_decision=risk_decision,
        trade_intent=trade_intent,
    )


def run_pipeline_from_research_row(
    row: dict,
    *,
    config: PipelineConfig | None = None,
) -> PipelineResult:
    """Build a DecisionInput from a generic row dict and run the shared pipeline."""

    return run_decision_pipeline(
        decision_input_from_research_row(row),
        config=config,
    )


def run_pipeline_batch(
    decision_inputs: list[DecisionInput],
    *,
    config: PipelineConfig | None = None,
) -> list[PipelineResult]:
    """Run the shared decision pipeline over a deterministic ordered batch of inputs."""

    return [
        run_decision_pipeline(decision_input, config=config)
        for decision_input in decision_inputs
    ]
