"""Dataclasses for generic edge signal decisions."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EdgeSignal:
    """Standardized edge signal built from fair-value estimates."""

    asset_class: str
    fair_probability: float | None
    market_implied_probability: float | None
    edge: float | None
    confidence: float | None
    liquidity_score: float | None
    signal_strength: float | None
    verdict: str
    reasons: list[str] = field(default_factory=list)
