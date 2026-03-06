"""Dataclasses for deterministic paper-trading decisions and outcomes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TradeDecision:
    """Normalized trade decision consumed by the paper-trading simulator."""

    asset_class: str
    decision: str
    size: float
    edge: float | None


@dataclass
class TradeResult:
    """Deterministic simulated trade result used for paper-trading accounting."""

    asset_class: str
    size: float
    entry_probability: float | None
    outcome: bool
    pnl: float
