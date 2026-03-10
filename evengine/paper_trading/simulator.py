"""Deterministic paper-trading simulation helpers."""

from __future__ import annotations

from evengine.paper_trading.trade_types import TradeDecision, TradeResult


def _decimal_odds_from_probability(entry_probability: float | None) -> float:
    """Convert an entry probability into decimal odds for stake-based PnL."""

    if entry_probability is None:
        raise ValueError("entry_probability is required for odds-aware paper trading")
    if entry_probability <= 0.0 or entry_probability > 1.0:
        raise ValueError("entry_probability must be greater than 0.0 and at most 1.0")
    return 1.0 / entry_probability


def simulate_trade(decision: TradeDecision, outcome: bool) -> TradeResult:
    """Simulate one trade decision with a boolean outcome."""

    if decision.decision != "bet":
        pnl: float = 0.0
        entry_odds: float | None = None
    elif outcome:
        entry_odds = _decimal_odds_from_probability(decision.entry_probability)
        pnl = decision.size * (entry_odds - 1.0)
    else:
        entry_odds = _decimal_odds_from_probability(decision.entry_probability)
        pnl = -decision.size

    return TradeResult(
        asset_class=decision.asset_class,
        size=decision.size,
        entry_probability=decision.entry_probability,
        entry_odds=entry_odds,
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
