"""Deterministic paper-trading simulation helpers."""

from __future__ import annotations

from evengine.paper_trading.trade_types import TradeDecision, TradeResult


def simulate_trade(decision: TradeDecision, outcome: bool) -> TradeResult:
    """Simulate one trade decision with a boolean outcome."""

    if decision.decision != "bet":
        pnl: float = 0.0
    elif outcome:
        pnl = decision.size
    else:
        pnl = -decision.size

    return TradeResult(
        asset_class=decision.asset_class,
        size=decision.size,
        entry_probability=None,
        outcome=outcome,
        pnl=pnl,
    )


def simulate_trades(
    decisions: list[TradeDecision],
    outcomes: list[bool],
) -> list[TradeResult]:
    """Simulate a deterministic batch of trade decisions in order."""

    if len(decisions) != len(outcomes):
        raise ValueError("decisions and outcomes must have the same length")
    return [simulate_trade(decision, outcome) for decision, outcome in zip(decisions, outcomes)]
