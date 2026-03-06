"""Dataclasses for generic risk gating."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RiskInput:
    """Generic input payload for deterministic risk review."""

    asset_class: str
    verdict: str
    edge: float | None
    confidence: float | None
    liquidity_score: float | None
    max_position_size: float | None
    current_exposure: float | None


@dataclass
class RiskDecision:
    """Deterministic portfolio-risk decision for a candidate signal."""

    asset_class: str
    approved: bool
    final_verdict: str
    recommended_size: float
    reasons: list[str] = field(default_factory=list)
