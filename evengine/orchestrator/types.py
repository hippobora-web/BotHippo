"""Dataclasses for deterministic WINA orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field

from evengine.live_adapters.types import RawMarketPrice


@dataclass
class OrchestratorInput:
    """Input payload for the deterministic end-to-end orchestrator."""

    raw_prices: list[RawMarketPrice] = field(default_factory=list)
    current_exposure: float = 0.0


@dataclass
class OrchestratorResult:
    """Aggregate outcome of one deterministic orchestration pass."""

    anomalies_detected: int
    trades_executed: int
    total_pnl: float
