"""Dataclasses for deterministic experiment tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExperimentRun:
    """One deterministic tracked strategy-discovery run."""

    strategy_config: dict
    total_pnl: float
    win_rate: float
    trades: int
    timestamp: float


@dataclass(frozen=True)
class ExperimentSummary:
    """Summary of tracked experiment runs and the current best run."""

    runs: list[ExperimentRun]
    best_run: ExperimentRun | None
