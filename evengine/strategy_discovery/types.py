"""Dataclasses for deterministic strategy discovery."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StrategyConfig:
    """Deterministic threshold configuration for one strategy candidate."""

    min_edge: float
    min_confidence: float
    min_liquidity: float


@dataclass(frozen=True)
class StrategyResult:
    """Performance summary for one evaluated strategy configuration."""

    config: StrategyConfig
    total_pnl: float
    win_rate: float
    trades: int
