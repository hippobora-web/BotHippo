"""Dataclasses for deterministic live paper trading."""

from __future__ import annotations

from dataclasses import dataclass, field

from evengine.analytics import PerformanceReport
from evengine.live_adapters import RawMarketPrice


@dataclass
class LivePaperTradingInput:
    """Input payload for a deterministic live paper trading run."""

    raw_prices: list[RawMarketPrice] = field(default_factory=list)
    current_exposure: float = 0.0


@dataclass
class LivePaperTradingRun:
    """Aggregate outcome of a deterministic live paper trading batch."""

    observations_count: int
    anomalies_count: int
    trades_executed: int
    total_pnl: float
    trades_settled: int = 0
    pnl_history: list[float] = field(default_factory=list)
    wins: int = 0
    losses: int = 0


@dataclass
class LivePaperTradingReport:
    """Paper trading run bundled with a deterministic performance report."""

    run: LivePaperTradingRun
    performance_report: PerformanceReport
