"""Deterministic strategy evolution helpers."""

from __future__ import annotations

from evengine.strategy_discovery import StrategyConfig
from evengine.strategy_evolution.types import StrategyMutation


_MIN_EDGE_BOUNDS: tuple[float, float] = (0.0, 0.20)
_UNIT_INTERVAL: tuple[float, float] = (0.0, 1.0)


def _clamp(value: float, bounds: tuple[float, float]) -> float:
    """Clamp a float value into inclusive bounds."""

    lower, upper = bounds
    return max(lower, min(upper, value))


def _mutate_with_deltas(
    config: StrategyConfig,
    *,
    min_edge_delta: float,
    min_confidence_delta: float,
    min_liquidity_delta: float,
    mutation_type: str,
) -> StrategyMutation:
    """Build one deterministic strategy mutation from explicit parameter deltas."""

    mutated_config = StrategyConfig(
        min_edge=_clamp(config.min_edge + min_edge_delta, _MIN_EDGE_BOUNDS),
        min_confidence=_clamp(config.min_confidence + min_confidence_delta, _UNIT_INTERVAL),
        min_liquidity=_clamp(config.min_liquidity + min_liquidity_delta, _UNIT_INTERVAL),
    )
    return StrategyMutation(
        base_config=config,
        mutated_config=mutated_config,
        mutation_type=mutation_type,
    )


def mutate_strategy(config: StrategyConfig) -> StrategyConfig:
    """Generate one default deterministic mutation from a base strategy config."""

    mutation: StrategyMutation = _mutate_with_deltas(
        config,
        min_edge_delta=0.01,
        min_confidence_delta=0.05,
        min_liquidity_delta=0.05,
        mutation_type="upward",
    )
    return mutation.mutated_config


def generate_mutations(configs: list[StrategyConfig]) -> list[StrategyConfig]:
    """Generate deterministic mutated strategy variants for each base config."""

    mutations: list[StrategyConfig] = []
    seen: set[tuple[float, float, float]] = set()

    for config in configs:
        candidates: list[StrategyMutation] = [
            _mutate_with_deltas(
                config,
                min_edge_delta=0.01,
                min_confidence_delta=0.05,
                min_liquidity_delta=0.05,
                mutation_type="upward",
            ),
            _mutate_with_deltas(
                config,
                min_edge_delta=-0.01,
                min_confidence_delta=-0.05,
                min_liquidity_delta=-0.05,
                mutation_type="downward",
            ),
        ]

        for mutation in candidates:
            mutated_config: StrategyConfig = mutation.mutated_config
            key: tuple[float, float, float] = (
                mutated_config.min_edge,
                mutated_config.min_confidence,
                mutated_config.min_liquidity,
            )
            if key in seen:
                continue
            if mutated_config == config:
                continue
            seen.add(key)
            mutations.append(mutated_config)

    return mutations
