"""Deterministic live paper trading runner built on the shared WINA pipeline."""

from __future__ import annotations

from evengine.analytics import build_performance_report
from evengine.core import clamp_probability
from evengine.decision_pipeline import run_decision_pipeline
from evengine.live_adapters import convert_batch
from evengine.live_adapters.types import RawMarketPrice
from evengine.live_paper_trading.types import LivePaperTradingInput, LivePaperTradingRun
from evengine.market_scanner import convert_anomaly_to_decision_input, scan_market_observations
from evengine.market_scanner.types import MarketObservation
from evengine.market_signals.signals import detect_price_drift, detect_volatility
from evengine.market_signals.types import MarketPricePoint
from evengine.portfolio_engine import PortfolioState, update_portfolio
from evengine.trade_execution_sim import execute_trade_intent, simulate_trade_outcome


def _group_price_points(raw_prices: list[RawMarketPrice]) -> dict[str, list[MarketPricePoint]]:
    """Group raw price points by asset class and sort them by timestamp."""

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



def _build_enriched_observations(raw_prices: list[RawMarketPrice]) -> list[MarketObservation]:
    """Convert raw prices into scanner observations enriched with deterministic signals."""

    base_observations: list[MarketObservation] = convert_batch(raw_prices)
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

    enriched: list[MarketObservation] = []
    for observation in base_observations:
        adjusted_reference_probability: float = observation.reference_probability
        adjusted_probability = clamp_probability(
            observation.market_probability + drift_map.get(observation.asset_class, 0.0)
        )
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



def _result_probability_from_model_probability(model_probability: float | None) -> float:
    """Map model probability to a deterministic binary paper-trading outcome probability."""

    if model_probability is not None and model_probability > 0.5:
        return 1.0
    return 0.0



def run_live_paper_trading(inp: LivePaperTradingInput) -> LivePaperTradingRun:
    """Run deterministic paper trading over a batch of raw market prices."""

    observations = _build_enriched_observations(inp.raw_prices)
    anomalies = scan_market_observations(observations)
    portfolio_state = PortfolioState(
        balance=0.0,
        trades=0,
        wins=0,
        losses=0,
        pnl_history=[],
    )
    trades_executed: int = 0

    for anomaly in anomalies:
        decision_input = convert_anomaly_to_decision_input(anomaly)
        pipeline_result = run_decision_pipeline(decision_input)
        simulated_trade = execute_trade_intent(pipeline_result.trade_intent)
        result_probability: float = _result_probability_from_model_probability(
            decision_input.model_probability
        )
        trade_pnl = simulate_trade_outcome(simulated_trade, result_probability)
        if not simulated_trade.executed:
            continue
        trades_executed += 1
        portfolio_state = update_portfolio(portfolio_state, trade_pnl)

    performance_report = build_performance_report(
        portfolio_state.pnl_history,
        portfolio_state.wins,
        portfolio_state.trades,
    )
    return LivePaperTradingRun(
        observations_count=len(observations),
        anomalies_count=len(anomalies),
        trades_executed=trades_executed,
        total_pnl=performance_report.total_pnl,
        pnl_history=list(portfolio_state.pnl_history),
        wins=portfolio_state.wins,
        losses=portfolio_state.losses,
    )
