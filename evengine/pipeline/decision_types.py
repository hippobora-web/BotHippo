"""Dataclasses for the generic end-to-end decision pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DecisionInput:
    """Input payload for the generic pricing-to-risk decision pipeline."""

    asset_class: str
    market_implied_probability: float | None
    model_probability: float | None
    confidence: float | None
    liquidity_score: float | None
    current_exposure: float


@dataclass
class DecisionOutput:
    """Final deterministic decision output assembled from pricing, signal, and risk layers."""

    asset_class: str
    fair_probability: float | None
    edge: float | None
    signal_verdict: str
    risk_verdict: str
    approved: bool
    recommended_size: float
    reasons: list[str] = field(default_factory=list)
