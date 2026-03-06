"""Risk agent applying deterministic bankroll and exposure controls."""

from __future__ import annotations

from evengine.agents.schemas import EventInput, QuantDecision, RiskDecision
from evengine.portfolio.bankroll import get_default_bankroll
from evengine.portfolio.exposure import (
    get_stub_competition_exposure_fraction,
    get_stub_current_open_bets_count,
    get_stub_daily_exposure_fraction,
)
from evengine.portfolio.limits import (
    max_bet_fraction,
    max_daily_fraction,
    max_open_bets,
    max_same_competition_exposure_fraction,
)
from evengine.portfolio.sizing import compute_capped_stake


def run_risk(
    *,
    event_input: EventInput,
    quant_decision: QuantDecision,
) -> RiskDecision:
    """Compute deterministic risk approval and stake recommendation."""

    bankroll_eur: float = get_default_bankroll()
    bet_fraction_cap: float = max_bet_fraction()
    daily_fraction_cap: float = max_daily_fraction()
    open_bets_cap: int = max_open_bets()
    competition_fraction_cap: float = max_same_competition_exposure_fraction()

    open_bets_count: int = get_stub_current_open_bets_count()
    daily_exposure_fraction: float = get_stub_daily_exposure_fraction()
    competition_exposure_fraction: float = get_stub_competition_exposure_fraction(
        event_input.competition
    )

    if quant_decision.decision != "BET":
        return RiskDecision(
            event_id=event_input.event_id,
            allowed=0,
            recommended_stake_eur=0.0,
            bankroll_fraction=0.0,
            risk_flags=["not_a_bet"],
            risk_reason="not_a_bet",
            kill_switch=0,
        )

    if open_bets_count >= open_bets_cap:
        return RiskDecision(
            event_id=event_input.event_id,
            allowed=0,
            recommended_stake_eur=0.0,
            bankroll_fraction=0.0,
            risk_flags=["max_open_bets_reached"],
            risk_reason="max_open_bets_reached",
            kill_switch=1,
        )

    if daily_exposure_fraction >= daily_fraction_cap:
        return RiskDecision(
            event_id=event_input.event_id,
            allowed=0,
            recommended_stake_eur=0.0,
            bankroll_fraction=0.0,
            risk_flags=["daily_limit_reached"],
            risk_reason="daily_limit_reached",
            kill_switch=1,
        )

    if competition_exposure_fraction >= competition_fraction_cap:
        return RiskDecision(
            event_id=event_input.event_id,
            allowed=0,
            recommended_stake_eur=0.0,
            bankroll_fraction=0.0,
            risk_flags=["competition_exposure_limit"],
            risk_reason="competition_exposure_limit",
            kill_switch=0,
        )

    proposed_fraction: float = 0.01
    if quant_decision.edge >= 0.08 and quant_decision.ev > 0:
        proposed_fraction = 0.015

    stake_eur, applied_fraction = compute_capped_stake(
        bankroll_eur=bankroll_eur,
        proposed_fraction=proposed_fraction,
        cap_fraction=bet_fraction_cap,
    )

    return RiskDecision(
        event_id=event_input.event_id,
        allowed=1,
        recommended_stake_eur=stake_eur,
        bankroll_fraction=applied_fraction,
        risk_flags=[],
        risk_reason="approved",
        kill_switch=0,
    )

