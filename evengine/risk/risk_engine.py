"""Deterministic risk sizing and approval helpers."""

from __future__ import annotations

from evengine.risk.types import RiskDecision
from evengine.signals.types import EdgeSignal


def compute_recommended_size(
    *,
    edge: float | None,
    confidence: float | None,
    liquidity_score: float | None,
    max_position_size: float | None = 1.0,
) -> float:
    """Compute deterministic recommended position size from signal quality."""

    if edge is None or edge <= 0.0 or confidence is None or liquidity_score is None:
        return 0.0

    size: float = edge
    size *= confidence
    size *= liquidity_score
    cap: float = 1.0 if max_position_size is None else max(0.0, max_position_size)
    return max(0.0, min(size, cap))


def build_risk_decision(
    signal: EdgeSignal,
    *,
    max_position_size: float = 1.0,
    max_total_exposure: float = 5.0,
    current_exposure: float = 0.0,
) -> RiskDecision:
    """Apply deterministic portfolio gating to an edge signal."""

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
