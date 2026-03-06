"""Dataclasses for deterministic strategy evolution."""

from __future__ import annotations

from dataclasses import dataclass

from evengine.strategy_discovery import StrategyConfig


@dataclass(frozen=True)
class StrategyMutation:
    """One deterministic mutation derived from a base strategy configuration."""

    base_config: StrategyConfig
    mutated_config: StrategyConfig
    mutation_type: str
