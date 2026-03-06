"""Deterministic simulated execution helpers for trade intents."""

from __future__ import annotations

from evengine.core import TradeIntent
from evengine.trade_execution_sim.types import SimulatedTrade, TradePnL


def execute_trade_intent(intent: TradeIntent) -> SimulatedTrade:
    """Convert a trade intent into a deterministic simulated trade."""

    return SimulatedTrade(
        asset_class=intent.asset_class,
        action=intent.action,
        size=intent.size,
        edge=intent.edge,
        executed=intent.action == "bet",
        reasons=list(intent.reasons),
    )



def simulate_trade_outcome(trade: SimulatedTrade, result_probability: float) -> TradePnL:
    """Simulate deterministic trade PnL from an execution flag and result probability."""

    if not trade.executed:
        return TradePnL(
            trade=trade,
            outcome=result_probability,
            pnl=0.0,
        )

    pnl: float = trade.size if result_probability > 0.5 else -trade.size
    return TradePnL(
        trade=trade,
        outcome=result_probability,
        pnl=pnl,
    )
