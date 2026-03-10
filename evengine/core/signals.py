"""Deterministic signal generation for the shared WINA decision core."""

from __future__ import annotations

from evengine.core.types import EdgeSignal, FairValueEstimate


def compute_signal_strength(
    *,
    edge: float | None,
    confidence: float | None,
    liquidity_score: float | None,
) -> float | None:
    """Compute deterministic signal strength from edge and quality factors."""

    if edge is None or confidence is None or liquidity_score is None:
        return None
    strength: float = edge
    strength *= confidence
    strength *= liquidity_score
    return strength


def build_edge_signal(
    estimate: FairValueEstimate,
    *,
    min_edge: float = 0.02,
    min_confidence: float = 0.50,
    min_liquidity: float = 0.30,
) -> EdgeSignal:
    """Build a standardized signal verdict from a fair-value estimate."""

    reasons: list[str] = []
    signal_strength: float | None = compute_signal_strength(
        edge=estimate.edge,
        confidence=estimate.confidence,
        liquidity_score=estimate.liquidity_score,
    )

    if estimate.fair_probability is None:
        reasons.append("fair probability is unavailable")
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="reject",
            reasons=reasons,
        )

    if estimate.market_implied_probability is None:
        reasons.append("market implied probability is unavailable")
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="reject",
            reasons=reasons,
        )

    if estimate.edge is None:
        reasons.append("edge is unavailable")
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="reject",
            reasons=reasons,
        )

    if estimate.edge <= 0.0:
        reasons.append("edge is non-positive")
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="reject",
            reasons=reasons,
        )

    if estimate.confidence is None:
        reasons.append("confidence is unavailable")
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="reject",
            reasons=reasons,
        )

    if estimate.liquidity_score is None:
        reasons.append("liquidity_score is unavailable")
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="reject",
            reasons=reasons,
        )

    if estimate.edge < min_edge:
        reasons.append(f"edge {estimate.edge:.4f} is below min_edge {min_edge:.4f}")
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="watch",
            reasons=reasons,
        )

    if estimate.confidence < min_confidence:
        reasons.append(
            f"confidence {estimate.confidence:.4f} is below min_confidence {min_confidence:.4f}"
        )
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="watch",
            reasons=reasons,
        )

    if estimate.liquidity_score < min_liquidity:
        reasons.append(
            f"liquidity_score {estimate.liquidity_score:.4f} is below min_liquidity {min_liquidity:.4f}"
        )
        return EdgeSignal(
            asset_class=estimate.asset_class,
            fair_probability=estimate.fair_probability,
            market_implied_probability=estimate.market_implied_probability,
            edge=estimate.edge,
            confidence=estimate.confidence,
            liquidity_score=estimate.liquidity_score,
            signal_strength=signal_strength,
            verdict="watch",
            reasons=reasons,
        )

    reasons.append(f"edge {estimate.edge:.4f} meets min_edge {min_edge:.4f}")
    reasons.append("confidence threshold passed")
    reasons.append("liquidity threshold passed")
    return EdgeSignal(
        asset_class=estimate.asset_class,
        fair_probability=estimate.fair_probability,
        market_implied_probability=estimate.market_implied_probability,
        edge=estimate.edge,
        confidence=estimate.confidence,
        liquidity_score=estimate.liquidity_score,
        signal_strength=signal_strength,
        verdict="bet",
        reasons=reasons,
    )
