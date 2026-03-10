"""Deterministic risk gating and trade-intent helpers for the shared core."""

from __future__ import annotations

from evengine.core.types import EdgeSignal, RiskDecision, TradeIntent


def compute_recommended_size(
    *,
    edge: float | None,
    confidence: float | None,
    liquidity_score: float | None,
    max_position_size: float = 1.0,
) -> float:
    """Compute a deterministic recommended position size from signal quality."""

    if edge is None or edge <= 0.0 or confidence is None or liquidity_score is None:
        return 0.0

    size: float = edge
    size *= confidence
    size *= liquidity_score
    return max(0.0, min(size, max_position_size))


def build_risk_decision(
    signal: EdgeSignal,
    *,
    max_position_size: float = 1.0,
    max_total_exposure: float = 5.0,
    current_exposure: float = 0.0,
) -> RiskDecision:
    """Apply deterministic risk gates to a signal before any future execution."""

    reasons: list[str] = []

    if signal.verdict != "bet":
        reasons.append(f"signal verdict is {signal.verdict}")
        return RiskDecision(
            asset_class=signal.asset_class,
            approved=False,
            final_verdict=signal.verdict,
            recommended_size=0.0,
            reasons=reasons,
        )

    recommended_size: float = compute_recommended_size(
        edge=signal.edge,
        confidence=signal.confidence,
        liquidity_score=signal.liquidity_score,
        max_position_size=max_position_size,
    )
    if recommended_size <= 0.0:
        reasons.append("recommended size is zero after risk sizing")
        return RiskDecision(
            asset_class=signal.asset_class,
            approved=False,
            final_verdict="reject",
            recommended_size=0.0,
            reasons=reasons,
        )

    proposed_exposure: float = current_exposure + recommended_size
    if proposed_exposure > max_total_exposure:
        reasons.append(
            "current exposure plus proposed size exceeds max_total_exposure "
            f"({current_exposure:.4f} + {recommended_size:.4f} > {max_total_exposure:.4f})"
        )
        return RiskDecision(
            asset_class=signal.asset_class,
            approved=False,
            final_verdict="reject",
            recommended_size=0.0,
            reasons=reasons,
        )

    reasons.append(f"recommended size {recommended_size:.4f} approved")
    return RiskDecision(
        asset_class=signal.asset_class,
        approved=True,
        final_verdict="bet",
        recommended_size=recommended_size,
        reasons=reasons,
    )


def build_trade_intent(
    *,
    signal: EdgeSignal,
    risk_decision: RiskDecision,
) -> TradeIntent:
    """Build an execution-agnostic trade intent from signal and risk outputs."""

    reasons: list[str] = []
    for reason in [*signal.reasons, *risk_decision.reasons]:
        if reason not in reasons:
            reasons.append(reason)

    return TradeIntent(
        asset_class=signal.asset_class,
        action="bet" if risk_decision.approved else "hold",
        approved=risk_decision.approved,
        size=risk_decision.recommended_size,
        edge=signal.edge,
        market_implied_probability=signal.market_implied_probability,
        reasons=reasons,
    )
