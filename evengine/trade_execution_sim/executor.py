"""Deterministic simulated execution helpers for trade intents."""

from __future__ import annotations

from evengine.core import TradeIntent
from evengine.trade_execution_sim.types import SimulatedTrade, TradePnL


def _decimal_odds_from_probability(entry_probability: float | None) -> float:
    """Convert an entry probability into decimal odds for stake-based PnL."""

    if entry_probability is None:
        raise ValueError("entry_probability is required for settled trade simulation")
    if entry_probability <= 0.0 or entry_probability > 1.0:
        raise ValueError("entry_probability must be greater than 0.0 and at most 1.0")
    return 1.0 / entry_probability


def execute_trade_intent(intent: TradeIntent) -> SimulatedTrade:
    """Convert a trade intent into a deterministic simulated trade."""

    return SimulatedTrade(
        asset_class=intent.asset_class,
        action=intent.action,
        size=intent.size,
        edge=intent.edge,
        entry_probability=intent.market_implied_probability,
        executed=intent.action == "bet",
        reasons=list(intent.reasons),
    )


def simulate_trade_outcome(trade: SimulatedTrade, settled_outcome: bool | None) -> TradePnL:
    """Simulate settled trade PnL when a real settlement outcome is available."""

    if not trade.executed or settled_outcome is None:
        return TradePnL(
            trade=trade,
            outcome=settled_outcome,
            pnl=0.0,
            settled=False,
        )

    entry_odds: float = _decimal_odds_from_probability(trade.entry_probability)
    pnl: float = trade.size * (entry_odds - 1.0) if settled_outcome else -trade.size
    return TradePnL(
        trade=trade,
        outcome=settled_outcome,
        pnl=pnl,
        settled=True,
    )
