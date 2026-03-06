"""Dataclasses for the generic strategy layer."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StrategyInput:
    """Input payload for running one dataset row through the strategy layer."""

    asset_class: str
    market_implied_probability: float | None
    model_probability: float | None
    confidence: float | None
    liquidity_score: float | None
    current_exposure: float


@dataclass
class StrategyDecision:
    """Final strategy-layer decision derived from the generic decision pipeline."""

    asset_class: str
    decision: str
    approved: bool
    size: float
    edge: float | None
    reasons: list[str] = field(default_factory=list)
