"""Dataclasses used by the deterministic runtime loop."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RuntimeConfig:
    """Fixed-interval runtime settings for the live paper-trading loop."""

    interval_seconds: int
    max_cycles: int | None

    def __post_init__(self) -> None:
        """Reject invalid negative runtime settings."""

        if self.interval_seconds < 0:
            raise ValueError("interval_seconds must be >= 0")
        if self.max_cycles is not None and self.max_cycles < 0:
            raise ValueError("max_cycles must be >= 0 when provided")


@dataclass
class RuntimeResult:
    """Aggregate runtime outcome across all completed cycles."""

    cycles_run: int
    total_trades: int
    total_pnl: float
