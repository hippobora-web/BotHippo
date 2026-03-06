"""Deterministic report builder for live paper trading runs."""

from __future__ import annotations

from evengine.analytics import build_performance_report
from evengine.live_paper_trading.types import LivePaperTradingReport, LivePaperTradingRun


def build_live_paper_trading_report(
    run: LivePaperTradingRun,
) -> LivePaperTradingReport:
    """Build a deterministic performance report from a live paper trading run."""

    performance_report = build_performance_report(
        run.pnl_history,
        run.wins,
        run.trades_executed,
    )
    return LivePaperTradingReport(
        run=run,
        performance_report=performance_report,
    )
