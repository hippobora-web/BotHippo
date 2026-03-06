"""Deterministic market anomaly scanning helpers."""

from __future__ import annotations

from evengine.core import DecisionInput
from evengine.market_scanner.types import MarketAnomaly, MarketObservation


def detect_probability_anomaly(obs: MarketObservation) -> MarketAnomaly | None:
    """Detect a deterministic probability divergence anomaly from one observation."""

    difference: float = abs(obs.reference_probability - obs.market_probability)
    if difference < 0.05:
        return None

    return MarketAnomaly(
        asset_class=obs.asset_class,
        market_probability=obs.market_probability,
        reference_probability=obs.reference_probability,
        anomaly_score=difference,
        reason="probability divergence",
    )



def scan_market_observations(
    observations: list[MarketObservation],
) -> list[MarketAnomaly]:
    """Scan observations deterministically and return only detected anomalies."""

    anomalies: list[MarketAnomaly] = []
    for observation in observations:
        anomaly: MarketAnomaly | None = detect_probability_anomaly(observation)
        if anomaly is not None:
            anomalies.append(anomaly)
    return anomalies



def convert_anomaly_to_decision_input(
    anomaly: MarketAnomaly,
) -> DecisionInput:
    """Convert a market anomaly into a shared-core decision input."""

    return DecisionInput(
        asset_class=anomaly.asset_class,
        source=None,
        event_id=None,
        market_id=None,
        selection_id=None,
        market_implied_probability=anomaly.market_probability,
        model_probability=anomaly.reference_probability,
        confidence=anomaly.anomaly_score,
        liquidity_score=None,
        current_exposure=0.0,
    )
