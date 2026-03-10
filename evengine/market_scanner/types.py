"""Dataclasses for deterministic market anomaly scanning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketObservation:
    """One normalized market observation used for anomaly detection."""

    asset_class: str
    market_probability: float
    reference_probability: float
    liquidity_score: float | None
    source: str | None = None
    event_id: str | None = None
    market_id: str | None = None
    selection_id: str | None = None
    settled_outcome: bool | None = None


@dataclass
class MarketAnomaly:
    """Detected deterministic market anomaly based on probability divergence."""

    asset_class: str
    market_probability: float
    reference_probability: float
    anomaly_score: float
    reason: str
    liquidity_score: float | None = None
    source: str | None = None
    event_id: str | None = None
    market_id: str | None = None
    selection_id: str | None = None
    settled_outcome: bool | None = None
