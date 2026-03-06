"""Dataclasses for deterministic market signal detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketPricePoint:
    """One normalized market probability observation at a point in time."""

    asset_class: str
    probability: float
    timestamp: float


@dataclass
class PriceDriftSignal:
    """Detected directional drift between the first and last market observations."""

    asset_class: str
    drift: float
    reason: str


@dataclass
class VolatilitySignal:
    """Detected probability volatility over a sequence of market observations."""

    asset_class: str
    volatility: float
    reason: str
