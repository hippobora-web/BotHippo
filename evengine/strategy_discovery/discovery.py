"""Deterministic strategy discovery built on scanner, decision pipeline, and simulation."""

from __future__ import annotations

from evengine.core import DecisionInput
from evengine.decision_pipeline import PipelineConfig, run_decision_pipeline
from evengine.market_scanner.scanner import (
    convert_anomaly_to_decision_input,
    scan_market_observations,
)
from evengine.market_scanner.types import MarketAnomaly, MarketObservation
from evengine.strategy_discovery.types import StrategyConfig, StrategyResult


def generate_strategy_configs() -> list[StrategyConfig]:
    """Generate a small deterministic grid of strategy threshold configurations."""

    return [
        StrategyConfig(
            min_edge=min_edge,
            min_confidence=min_confidence,
            min_liquidity=min_liquidity,
        )
        for min_edge in (0.02, 0.05, 0.08)
        for min_confidence in (0.50, 0.70)
        for min_liquidity in (0.30, 0.50)
    ]


def _observation_key(observation: MarketObservation) -> tuple[str, float, float]:
    """Build a deterministic lookup key for one market observation."""

    return (
        observation.asset_class,
        observation.market_probability,
        observation.reference_probability,
    )


def _anomaly_key(anomaly: MarketAnomaly) -> tuple[str, float, float]:
    """Build a deterministic lookup key for one anomaly."""

    return (
        anomaly.asset_class,
        anomaly.market_probability,
        anomaly.reference_probability,
    )


def _build_observation_lookup(
    observations: list[MarketObservation],
) -> dict[tuple[str, float, float], list[MarketObservation]]:
    """Build a deterministic mapping from anomaly-equivalent keys to observations."""

    lookup: dict[tuple[str, float, float], list[MarketObservation]] = {}
    for observation in observations:
        key: tuple[str, float, float] = _observation_key(observation)
        lookup.setdefault(key, []).append(observation)
    return lookup


def _decision_input_from_anomaly(
    anomaly: MarketAnomaly,
    observation: MarketObservation,
) -> DecisionInput:
    """Build a decision input from an anomaly while preserving liquidity context."""

    base_input: DecisionInput = convert_anomaly_to_decision_input(anomaly)
    return DecisionInput(
        asset_class=base_input.asset_class,
        source=base_input.source,
        event_id=base_input.event_id,
        market_id=base_input.market_id,
        selection_id=base_input.selection_id,
        market_implied_probability=base_input.market_implied_probability,
        model_probability=base_input.model_probability,
        confidence=base_input.confidence,
        liquidity_score=observation.liquidity_score,
        current_exposure=base_input.current_exposure,
    )


def _pipeline_config_from_strategy_config(config: StrategyConfig) -> PipelineConfig:
    """Convert a strategy configuration into a decision pipeline configuration."""

    return PipelineConfig(
        min_edge=config.min_edge,
        min_confidence=config.min_confidence,
        min_liquidity=config.min_liquidity,
    )


def evaluate_strategy(
    config: StrategyConfig,
    observations: list[MarketObservation],
) -> StrategyResult:
    """Evaluate one strategy configuration over observed market anomalies."""

    anomalies: list[MarketAnomaly] = scan_market_observations(observations)
    observation_lookup: dict[tuple[str, float, float], list[MarketObservation]] = (
        _build_observation_lookup(observations)
    )
    pipeline_config: PipelineConfig = _pipeline_config_from_strategy_config(config)
    approved_trades: int = 0

    for anomaly in anomalies:
        matching_observations: list[MarketObservation] = observation_lookup.get(_anomaly_key(anomaly), [])
        if not matching_observations:
            continue
        observation: MarketObservation = matching_observations.pop(0)
        decision_input: DecisionInput = _decision_input_from_anomaly(anomaly, observation)
        pipeline_result = run_decision_pipeline(decision_input, config=pipeline_config)
        if pipeline_result.trade_intent.approved:
            approved_trades += 1

    return StrategyResult(
        config=config,
        total_pnl=0.0,
        win_rate=0.0,
        trades=approved_trades,
    )


def discover_strategies(observations: list[MarketObservation]) -> list[StrategyResult]:
    """Run deterministic strategy discovery and rank strategies by performance."""

    results: list[StrategyResult] = [
        evaluate_strategy(config, observations)
        for config in generate_strategy_configs()
    ]
    return sorted(
        results,
        key=lambda result: (
            -result.total_pnl,
            -result.win_rate,
            -result.trades,
            result.config.min_edge,
            result.config.min_confidence,
            result.config.min_liquidity,
        ),
    )
