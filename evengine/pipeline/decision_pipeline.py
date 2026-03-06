"""Deterministic end-to-end decision pipeline wiring pricing, signals, and risk."""

from __future__ import annotations

from evengine.pipeline.decision_types import DecisionInput, DecisionOutput
from evengine.pricing.fair_value import build_fair_value_estimate
from evengine.pricing.types import FairValueInput
from evengine.risk.risk_engine import build_risk_decision
from evengine.signals.edge_engine import build_edge_signal


def _combined_reasons(*reason_lists: list[str]) -> list[str]:
    """Combine ordered reason lists while avoiding duplicates."""

    combined: list[str] = []
    for reasons in reason_lists:
        for reason in reasons:
            if reason not in combined:
                combined.append(reason)
    return combined


def run_decision_pipeline(inp: DecisionInput) -> DecisionOutput:
    """Run the deterministic pricing -> signal -> risk pipeline."""

    fair_value_input = FairValueInput(
        asset_class=inp.asset_class,
        market_implied_probability=inp.market_implied_probability,
        model_probability=inp.model_probability,
        confidence=inp.confidence,
        liquidity_score=inp.liquidity_score,
    )
    estimate = build_fair_value_estimate(fair_value_input)
    signal = build_edge_signal(estimate)
    risk_decision = build_risk_decision(
        signal,
        current_exposure=inp.current_exposure,
    )
    return DecisionOutput(
        asset_class=inp.asset_class,
        fair_probability=estimate.fair_probability,
        edge=estimate.edge,
        signal_verdict=signal.verdict,
        risk_verdict=risk_decision.final_verdict,
        approved=risk_decision.approved,
        recommended_size=risk_decision.recommended_size,
        reasons=_combined_reasons(signal.reasons, risk_decision.reasons),
    )


def build_decision_from_probabilities(
    *,
    asset_class: str,
    market_implied_probability: float | None,
    model_probability: float | None,
    confidence: float | None,
    liquidity_score: float | None,
    current_exposure: float = 0.0,
) -> DecisionOutput:
    """Build a DecisionOutput directly from probability-style inputs."""

    return run_decision_pipeline(
        DecisionInput(
            asset_class=asset_class,
            market_implied_probability=market_implied_probability,
            model_probability=model_probability,
            confidence=confidence,
            liquidity_score=liquidity_score,
            current_exposure=current_exposure,
        )
    )
