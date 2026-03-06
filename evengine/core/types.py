"""Core dataclasses shared across deterministic WINA decision layers."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DecisionInput:
    """Generic input payload shared across market, research, and execution layers."""

    asset_class: str
    source: str | None
    event_id: str | None
    market_id: str | None
    selection_id: str | None
    market_implied_probability: float | None
    model_probability: float | None
    confidence: float | None
    liquidity_score: float | None
    current_exposure: float | None


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


@dataclass
class EdgeSignal:
    """Standardized edge signal produced from a fair-value estimate."""

    asset_class: str
    fair_probability: float | None
    market_implied_probability: float | None
    edge: float | None
    confidence: float | None
    liquidity_score: float | None
    signal_strength: float | None
    verdict: str
    reasons: list[str] = field(default_factory=list)


@dataclass
class RiskDecision:
    """Deterministic risk gate decision for a candidate trade idea."""

    asset_class: str
    approved: bool
    final_verdict: str
    recommended_size: float
    reasons: list[str] = field(default_factory=list)


@dataclass
class TradeIntent:
    """Final execution-agnostic trade intent derived from signal and risk outputs."""

    asset_class: str
    action: str
    approved: bool
    size: float
    edge: float | None
    reasons: list[str] = field(default_factory=list)
