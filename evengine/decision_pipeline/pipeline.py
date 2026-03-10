"""Deterministic orchestration layer for the shared WINA decision core."""

from __future__ import annotations

import math

from evengine.core import (
    DecisionInput,
    EdgeSignal,
    FairValueEstimate,
    RiskDecision,
    TradeIntent,
    build_edge_signal,
    build_fair_value_estimate,
    build_risk_decision,
    build_trade_intent,
    decision_input_from_research_row,
)
from evengine.decision_pipeline.types import PipelineConfig, PipelineResult


def _combined_reasons(*reason_lists: list[str]) -> list[str]:
    """Combine ordered reason lists while avoiding duplicates."""

    combined: list[str] = []
    for reasons in reason_lists:
        for reason in reasons:
            if reason not in combined:
                combined.append(reason)
    return combined


def _has_text(value: str | None) -> bool:
    """Return whether a string-like field contains meaningful text."""

    return value is not None and bool(value.strip())


def _is_finite_number(value: float | None) -> bool:
    """Return whether a value is a finite float."""

    return value is not None and math.isfinite(value)


def _validate_probability(
    *,
    value: float | None,
    field_name: str,
    allow_zero: bool,
) -> str | None:
    """Return a validation error for a probability field, if any."""

    if value is None:
        return f"{field_name} is required"
    if not math.isfinite(value):
        return f"{field_name} must be finite"
    lower_bound: float = 0.0 if allow_zero else 0.0
    if allow_zero:
        if value < lower_bound or value > 1.0:
            return f"{field_name} must be between 0.0 and 1.0"
    elif value <= 0.0 or value > 1.0:
        return f"{field_name} must be greater than 0.0 and at most 1.0"
    return None


def _validate_unit_interval(value: float | None, field_name: str) -> str | None:
    """Return a validation error for a [0, 1] score field, if any."""

    if value is None:
        return f"{field_name} is required"
    if not math.isfinite(value):
        return f"{field_name} must be finite"
    if value < 0.0 or value > 1.0:
        return f"{field_name} must be between 0.0 and 1.0"
    return None


def _validate_decision_input(decision_input: DecisionInput) -> list[str]:
    """Return ordered validation errors for one decision input."""

    reasons: list[str] = []

    if not _has_text(decision_input.asset_class):
        reasons.append("asset_class is required")
    if not _has_text(decision_input.event_id):
        reasons.append("event_id is required")
    if not _has_text(decision_input.market_id):
        reasons.append("market_id is required")
    if not _has_text(decision_input.selection_id):
        reasons.append("selection_id is required")

    for reason in (
        _validate_probability(
            value=decision_input.market_implied_probability,
            field_name="market_implied_probability",
            allow_zero=False,
        ),
        _validate_probability(
            value=decision_input.model_probability,
            field_name="model_probability",
            allow_zero=True,
        ),
        _validate_unit_interval(decision_input.confidence, "confidence"),
        _validate_unit_interval(decision_input.liquidity_score, "liquidity_score"),
    ):
        if reason is not None:
            reasons.append(reason)

    if decision_input.current_exposure is None:
        reasons.append("current_exposure is required")
    elif not _is_finite_number(decision_input.current_exposure):
        reasons.append("current_exposure must be finite")
    elif decision_input.current_exposure < 0.0:
        reasons.append("current_exposure must be non-negative")

    return reasons


def _build_rejected_pipeline_result(
    decision_input: DecisionInput,
    *,
    reasons: list[str],
) -> PipelineResult:
    """Build a consistent rejected pipeline result for invalid input."""

    fair_value = FairValueEstimate(
        asset_class=decision_input.asset_class,
        market_implied_probability=decision_input.market_implied_probability,
        model_probability=decision_input.model_probability,
        fair_probability=None,
        edge=None,
        confidence=decision_input.confidence,
        liquidity_score=decision_input.liquidity_score,
    )
    edge_signal = EdgeSignal(
        asset_class=decision_input.asset_class,
        fair_probability=None,
        market_implied_probability=decision_input.market_implied_probability,
        edge=None,
        confidence=decision_input.confidence,
        liquidity_score=decision_input.liquidity_score,
        signal_strength=None,
        verdict="reject",
        reasons=list(reasons),
    )
    risk_reasons: list[str] = _combined_reasons(reasons, ["input validation failed"])
    risk_decision = RiskDecision(
        asset_class=decision_input.asset_class,
        approved=False,
        final_verdict="reject",
        recommended_size=0.0,
        reasons=risk_reasons,
    )
    trade_intent = TradeIntent(
        asset_class=decision_input.asset_class,
        action="hold",
        approved=False,
        size=0.0,
        edge=None,
        market_implied_probability=decision_input.market_implied_probability,
        reasons=risk_reasons,
    )
    return PipelineResult(
        decision_input=decision_input,
        fair_value=fair_value,
        edge_signal=edge_signal,
        risk_decision=risk_decision,
        trade_intent=trade_intent,
    )


def run_decision_pipeline(
    decision_input: DecisionInput,
    *,
    config: PipelineConfig | None = None,
) -> PipelineResult:
    """Run the shared deterministic decision pipeline for one decision input."""

    validation_errors: list[str] = _validate_decision_input(decision_input)
    if validation_errors:
        return _build_rejected_pipeline_result(
            decision_input,
            reasons=validation_errors,
        )

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
