"""Dataclasses for deterministic simulated trade execution."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SimulatedTrade:
    """Execution-agnostic simulated trade derived from a trade intent."""

    asset_class: str
    action: str
    size: float
    edge: float | None
    executed: bool
    entry_probability: float | None = None
    reasons: list[str] = field(default_factory=list)


@dataclass
class TradePnL:
    """Deterministic PnL event associated with one simulated trade."""

    trade: SimulatedTrade
    outcome: bool | None
    pnl: float
    settled: bool = False
