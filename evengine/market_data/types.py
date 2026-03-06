"""Core dataclasses for deterministic market data snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class MarketSelection:
    """One market selection with raw and fair probability fields."""

    selection_id: str
    label: str
    odds: float | None = None
    price: float | None = None
    implied_probability_raw: float | None = None
    implied_probability_fair: float | None = None


@dataclass
class MarketSnapshot:
    """One collected market snapshot from a sportsbook or prediction market source."""

    snapshot_id: str
    event_id: str
    market_id: str
    source: str
    market_name: str
    collected_at: datetime
    starts_at: datetime | None = None
    selections: list[MarketSelection] = field(default_factory=list)
    overround: float | None = None
