"""Deterministic live paper trading runner built on the shared WINA pipeline."""

from __future__ import annotations

from evengine.analytics import build_performance_report
from evengine.decision_pipeline import run_decision_pipeline
from evengine.live_adapters import build_enriched_observations
from evengine.live_paper_trading.types import LivePaperTradingInput, LivePaperTradingRun
from evengine.market_scanner import convert_anomaly_to_decision_input, scan_market_observations
from evengine.portfolio_engine import PortfolioState, update_portfolio
from evengine.trade_execution_sim import execute_trade_intent, simulate_trade_outcome


def run_live_paper_trading(inp: LivePaperTradingInput) -> LivePaperTradingRun:
    """Run deterministic paper trading over a batch of raw market prices."""

    observations = build_enriched_observations(inp.raw_prices)
    anomalies = scan_market_observations(observations)
    portfolio_state = PortfolioState(
        balance=0.0,
        trades=0,
        wins=0,
        losses=0,
        pnl_history=[],
    )
    current_exposure: float = inp.current_exposure
    trades_executed: int = 0
    trades_settled: int = 0

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
        if not trade_pnl.settled:
            continue

        trades_settled += 1
        current_exposure = max(0.0, current_exposure - simulated_trade.size)
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
        trades_settled=trades_settled,
        total_pnl=performance_report.total_pnl,
        pnl_history=list(portfolio_state.pnl_history),
        wins=portfolio_state.wins,
        losses=portfolio_state.losses,
    )
