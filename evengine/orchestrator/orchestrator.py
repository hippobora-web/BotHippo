"""Deterministic end-to-end orchestration across WINA pipeline layers."""

from __future__ import annotations

from evengine.decision_pipeline import run_decision_pipeline
from evengine.live_adapters import build_enriched_observations
from evengine.market_scanner import convert_anomaly_to_decision_input, scan_market_observations
from evengine.orchestrator.types import OrchestratorInput, OrchestratorResult
from evengine.portfolio_engine import PortfolioState, compute_portfolio_metrics, update_portfolio
from evengine.trade_execution_sim import execute_trade_intent, simulate_trade_outcome


def run_orchestrator(input: OrchestratorInput) -> OrchestratorResult:
    """Run the deterministic WINA pipeline end-to-end on raw market prices."""

    observations = build_enriched_observations(input.raw_prices)
    anomalies = scan_market_observations(observations)
    portfolio_state = PortfolioState(
        balance=0.0,
        trades=0,
        wins=0,
        losses=0,
        pnl_history=[],
    )
    current_exposure: float = input.current_exposure
    trades_executed: int = 0

    for anomaly in anomalies:
        decision_input = convert_anomaly_to_decision_input(
            anomaly,
            current_exposure=current_exposure,
        )
        pipeline_result = run_decision_pipeline(decision_input)
        simulated_trade = execute_trade_intent(pipeline_result.trade_intent)
        if not simulated_trade.executed:
            continue

        trades_executed += 1
        current_exposure += simulated_trade.size
        trade_pnl = simulate_trade_outcome(simulated_trade, anomaly.settled_outcome)
        if trade_pnl.settled:
            current_exposure = max(0.0, current_exposure - simulated_trade.size)
            portfolio_state = update_portfolio(portfolio_state, trade_pnl)

    metrics = compute_portfolio_metrics(portfolio_state)
    return OrchestratorResult(
        anomalies_detected=len(anomalies),
        trades_executed=trades_executed,
        total_pnl=metrics.total_pnl,
    )
