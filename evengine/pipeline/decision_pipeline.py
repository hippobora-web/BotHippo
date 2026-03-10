"""Compatibility wrapper delegating legacy pipeline calls to the shared decision core."""

from __future__ import annotations

from evengine.core.types import DecisionInput as SharedDecisionInput
from evengine.decision_pipeline import run_decision_pipeline as run_shared_decision_pipeline
from evengine.pipeline.decision_types import DecisionInput, DecisionOutput


def _combined_reasons(*reason_lists: list[str]) -> list[str]:
    """Combine ordered reason lists while avoiding duplicates."""

    combined: list[str] = []
    for reasons in reason_lists:
        for reason in reasons:
            if reason not in combined:
                combined.append(reason)
    return combined


def _to_shared_decision_input(inp: DecisionInput) -> SharedDecisionInput:
    """Map the legacy pipeline input onto the shared decision input."""

    return SharedDecisionInput(
        asset_class=inp.asset_class,
        source=inp.source,
        event_id=inp.event_id,
        market_id=inp.market_id,
        selection_id=inp.selection_id,
        market_implied_probability=inp.market_implied_probability,
        model_probability=inp.model_probability,
        confidence=inp.confidence,
        liquidity_score=inp.liquidity_score,
        current_exposure=inp.current_exposure,
    )


def run_decision_pipeline(inp: DecisionInput) -> DecisionOutput:
    """Run the shared decision pipeline through the legacy output contract."""

    pipeline_result = run_shared_decision_pipeline(_to_shared_decision_input(inp))
    return DecisionOutput(
        asset_class=inp.asset_class,
        fair_probability=pipeline_result.fair_value.fair_probability,
        edge=pipeline_result.fair_value.edge,
        signal_verdict=pipeline_result.edge_signal.verdict,
        risk_verdict=pipeline_result.risk_decision.final_verdict,
        approved=pipeline_result.risk_decision.approved,
        recommended_size=pipeline_result.risk_decision.recommended_size,
        reasons=_combined_reasons(
            pipeline_result.edge_signal.reasons,
            pipeline_result.risk_decision.reasons,
        ),
    )


def build_decision_from_probabilities(
    *,
    asset_class: str,
    market_implied_probability: float | None,
    model_probability: float | None,
    confidence: float | None,
    liquidity_score: float | None,
    current_exposure: float = 0.0,
    source: str | None = None,
    event_id: str | None = None,
    market_id: str | None = None,
    selection_id: str | None = None,
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
            source=source,
            event_id=event_id,
            market_id=market_id,
            selection_id=selection_id,
        )
    )
