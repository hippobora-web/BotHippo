"""Deterministic signal detection for market probability paths."""

from __future__ import annotations

from evengine.market_signals.types import MarketPricePoint, PriceDriftSignal, VolatilitySignal



def detect_price_drift(points: list[MarketPricePoint]) -> PriceDriftSignal | None:
    """Detect material drift between the first and last probability observations."""

    if len(points) < 2:
        return None

    drift: float = points[-1].probability - points[0].probability
    if abs(drift) < 0.05:
        return None

    return PriceDriftSignal(
        asset_class=points[-1].asset_class,
        drift=drift,
        reason="price drift",
    )



def detect_volatility(points: list[MarketPricePoint]) -> VolatilitySignal | None:
    """Detect material volatility from the simple variance of probabilities."""

    if len(points) < 2:
        return None

    probabilities: list[float] = [point.probability for point in points]
    mean_probability: float = sum(probabilities) / len(probabilities)
    variance: float = sum((probability - mean_probability) ** 2 for probability in probabilities) / len(probabilities)

    if variance < 0.01:
        return None

    return VolatilitySignal(
        asset_class=points[-1].asset_class,
        volatility=variance,
        reason="probability volatility",
    )
