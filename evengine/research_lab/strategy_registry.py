"""Deterministic JSON registry helpers for research lab strategy specs."""

from __future__ import annotations

import json
from pathlib import Path

from evengine.research_lab.schemas import StrategySpec


def _sorted_strategies(strategies: list[StrategySpec]) -> list[StrategySpec]:
    """Return strategies sorted deterministically by strategy_id."""

    return sorted(strategies, key=lambda strategy: strategy.strategy_id)


def load_registry(path: str) -> list[StrategySpec]:
    """Load the local strategy registry from JSON, returning an empty list if missing."""

    registry_path: Path = Path(path)
    if not registry_path.exists():
        return []

    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("strategy_registry must contain a list")

    strategies: list[StrategySpec] = [StrategySpec.model_validate(item) for item in payload]
    return _sorted_strategies(strategies)


def save_registry(path: str, strategies: list[StrategySpec]) -> None:
    """Persist the local strategy registry as deterministic JSON."""

    registry_path: Path = Path(path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    ordered_strategies: list[StrategySpec] = _sorted_strategies(strategies)
    payload: list[dict] = [strategy.model_dump() for strategy in ordered_strategies]
    registry_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def upsert_strategy(path: str, strategy: StrategySpec) -> None:
    """Insert or replace a strategy in the local registry by strategy_id."""

    existing_strategies: list[StrategySpec] = load_registry(path)
    updated_strategies: list[StrategySpec] = [
        existing_strategy
        for existing_strategy in existing_strategies
        if existing_strategy.strategy_id != strategy.strategy_id
    ]
    updated_strategies.append(strategy)
    save_registry(path, updated_strategies)


def get_strategy(path: str, strategy_id: str) -> StrategySpec | None:
    """Return one strategy from the local registry or None when absent."""

    for strategy in load_registry(path):
        if strategy.strategy_id == strategy_id:
            return strategy
    return None
