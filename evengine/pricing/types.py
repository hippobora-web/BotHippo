"""Dataclasses for generic cross-market fair-value estimation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FairValueInput:
    """Input payload for building a fair-value estimate."""

    asset_class: str
    market_implied_probability: float | None
    model_probability: float | None
    confidence: float | None
    liquidity_score: float | None


@dataclass
class FairValueEstimate:
    """Deterministic fair-value estimate built from market and model probabilities."""

    asset_class: str
    market_implied_probability: float | None
    model_probability: float | None
    fair_probability: float | None
    edge: float | None
    confidence: float | None
    liquidity_score: float | None
