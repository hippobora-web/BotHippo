"""Pure deterministic helpers for fair-value estimation."""

from __future__ import annotations

from evengine.pricing.types import FairValueEstimate, FairValueInput


def clamp_probability(value: float | None) -> float | None:
    """Clamp a probability into the closed interval [0.0, 1.0]."""

    if value is None:
        return None
    return max(0.0, min(1.0, value))


def compute_edge(
    model_probability: float | None,
    market_implied_probability: float | None,
) -> float | None:
    """Compute edge as model minus market implied probability."""

    if model_probability is None or market_implied_probability is None:
        return None
    return model_probability - market_implied_probability


def build_fair_value_estimate(inp: FairValueInput) -> FairValueEstimate:
    """Build a deterministic fair-value estimate from normalized probabilities."""

    clamped_market_probability: float | None = clamp_probability(inp.market_implied_probability)
    clamped_model_probability: float | None = clamp_probability(inp.model_probability)
    fair_probability: float | None = clamped_model_probability
    edge: float | None = compute_edge(fair_probability, clamped_market_probability)
    return FairValueEstimate(
        asset_class=inp.asset_class,
        market_implied_probability=clamped_market_probability,
        model_probability=clamped_model_probability,
        fair_probability=fair_probability,
        edge=edge,
        confidence=inp.confidence,
        liquidity_score=inp.liquidity_score,
    )
