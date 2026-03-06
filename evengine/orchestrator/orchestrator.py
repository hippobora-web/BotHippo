"""Deterministic end-to-end orchestration across WINA pipeline layers."""

from __future__ import annotations

from evengine.core import DecisionInput, clamp_probability
from evengine.decision_pipeline import run_decision_pipeline
from evengine.live_adapters import convert_batch
from evengine.live_adapters.types import RawMarketPrice
from evengine.market_scanner.scanner import detect_probability_anomaly, scan_market_observations
from evengine.market_scanner.types import MarketAnomaly, MarketObservation
from evengine.market_signals.signals import detect_price_drift, detect_volatility
from evengine.market_signals.types import MarketPricePoint
from evengine.orchestrator.types import OrchestratorInput, OrchestratorResult
from evengine.portfolio_engine import PortfolioState, compute_portfolio_metrics, update_portfolio
from evengine.trade_execution_sim import execute_trade_intent, simulate_trade_outcome


def _group_price_points(raw_prices: list[RawMarketPrice]) -> dict[str, list[MarketPricePoint]]:
    """Group raw prices by asset class and sort each group by timestamp."""

    grouped: dict[str, list[MarketPricePoint]] = {}
    for raw_price in raw_prices:
        grouped.setdefault(raw_price.asset_class, []).append(
            MarketPricePoint(
                asset_class=raw_price.asset_class,
                probability=raw_price.probability,
                timestamp=raw_price.timestamp,
            )
        )
    for asset_class, points in grouped.items():
        grouped[asset_class] = sorted(points, key=lambda point: point.timestamp)
    return grouped


def _build_signal_maps(raw_prices: list[RawMarketPrice]) -> tuple[dict[str, float], dict[str, float]]:
    """Build deterministic drift and volatility maps keyed by asset class."""

    grouped_points: dict[str, list[MarketPricePoint]] = _group_price_points(raw_prices)
    drift_map: dict[str, float] = {}
    volatility_map: dict[str, float] = {}

    for asset_class in sorted(grouped_points):
        points: list[MarketPricePoint] = grouped_points[asset_class]
        drift_signal = detect_price_drift(points)
        volatility_signal = detect_volatility(points)
        if drift_signal is not None:
            drift_map[asset_class] = drift_signal.drift
        if volatility_signal is not None:
            volatility_map[asset_class] = volatility_signal.volatility

    return drift_map, volatility_map


def _build_enriched_observations(raw_prices: list[RawMarketPrice]) -> list[MarketObservation]:
    """Convert raw prices to observations enriched with deterministic market signals."""

    base_observations: list[MarketObservation] = convert_batch(raw_prices)
    drift_map, volatility_map = _build_signal_maps(raw_prices)
    enriched: list[MarketObservation] = []

    for observation in base_observations:
        adjusted_reference_probability: float = observation.reference_probability
        drift: float = drift_map.get(observation.asset_class, 0.0)
        adjusted_probability = clamp_probability(observation.market_probability + drift)
        if adjusted_probability is not None:
            adjusted_reference_probability = adjusted_probability

        volatility: float | None = volatility_map.get(observation.asset_class)
        liquidity_score: float | None = None
        if volatility is not None:
            liquidity_score = max(0.0, min(1.0, 1.0 - volatility))

        enriched.append(
            MarketObservation(
                asset_class=observation.asset_class,
                market_probability=observation.market_probability,
                reference_probability=adjusted_reference_probability,
                liquidity_score=liquidity_score,
            )
        )

    return enriched


def _build_decision_input(observation: MarketObservation, anomaly: MarketAnomaly) -> DecisionInput:
    """Build a shared-core decision input from an enriched observation and anomaly."""

    return DecisionInput(
        asset_class=anomaly.asset_class,
        source=None,
        event_id=None,
        market_id=None,
        selection_id=None,
        market_implied_probability=anomaly.market_probability,
        model_probability=anomaly.reference_probability,
        confidence=anomaly.anomaly_score,
        liquidity_score=observation.liquidity_score,
        current_exposure=0.0,
    )


def run_orchestrator(input: OrchestratorInput) -> OrchestratorResult:
    """Run the deterministic WINA pipeline end-to-end on raw market prices."""

    observations: list[MarketObservation] = _build_enriched_observations(input.raw_prices)
    anomalies: list[MarketAnomaly] = scan_market_observations(observations)
    portfolio_state: PortfolioState = PortfolioState(
        balance=0.0,
        trades=0,
        wins=0,
        losses=0,
        pnl_history=[],
    )
    trades_executed: int = 0

    for observation in observations:
        anomaly: MarketAnomaly | None = detect_probability_anomaly(observation)
        if anomaly is None:
            continue
        decision_input: DecisionInput = _build_decision_input(observation, anomaly)
        pipeline_result = run_decision_pipeline(decision_input)
        simulated_trade = execute_trade_intent(pipeline_result.trade_intent)
        trade_pnl = simulate_trade_outcome(simulated_trade, observation.reference_probability)
        portfolio_state = update_portfolio(portfolio_state, trade_pnl)
        if simulated_trade.executed:
            trades_executed += 1

    metrics = compute_portfolio_metrics(portfolio_state)
    return OrchestratorResult(
        anomalies_detected=len(anomalies),
        trades_executed=trades_executed,
        total_pnl=metrics.total_pnl,
    )
