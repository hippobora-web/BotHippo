"""Deterministic converters from raw market prices to scanner observations."""

from __future__ import annotations

from evengine.live_adapters.types import RawMarketPrice
from evengine.market_scanner.types import MarketObservation
from evengine.market_signals.signals import detect_price_drift, detect_volatility
from evengine.market_signals.types import MarketPricePoint


def _instrument_key(raw: RawMarketPrice) -> tuple[str, str | None, str | None, str | None]:
    """Build a stable instrument key for rolling observation state."""

    return (
        raw.asset_class,
        raw.event_id,
        raw.market_id,
        raw.selection_id,
    )


def _ordered_raw_prices(raw_prices: list[RawMarketPrice]) -> list[RawMarketPrice]:
    """Return raw prices in deterministic chronological order."""

    return [
        raw_price
        for _, raw_price in sorted(
            enumerate(raw_prices),
            key=lambda item: (item[1].timestamp, item[0]),
        )
    ]


def _project_reference_probability(history: list[MarketPricePoint], raw: RawMarketPrice) -> float:
    """Project a reference probability using only past observations."""

    if not history:
        return raw.probability

    reference_probability: float = history[-1].probability
    drift_signal = detect_price_drift(history)
    if drift_signal is None:
        return reference_probability

    projected_probability: float = reference_probability + drift_signal.drift
    if 0.0 <= projected_probability <= 1.0:
        return projected_probability
    return reference_probability


def _liquidity_from_history(history: list[MarketPricePoint]) -> float | None:
    """Derive a liquidity proxy from historical volatility observed so far."""

    volatility_signal = detect_volatility(history)
    if volatility_signal is None:
        return None
    return max(0.0, min(1.0, 1.0 - volatility_signal.volatility))


def convert_raw_to_observation(raw: RawMarketPrice) -> MarketObservation:
    """Convert one raw market price into a market observation for scanning."""

    return MarketObservation(
        asset_class=raw.asset_class,
        market_probability=raw.probability,
        reference_probability=raw.probability,
        liquidity_score=None,
        source=raw.source,
        event_id=raw.event_id,
        market_id=raw.market_id,
        selection_id=raw.selection_id,
        settled_outcome=raw.settled_outcome,
    )


def convert_batch(raw_prices: list[RawMarketPrice]) -> list[MarketObservation]:
    """Convert a batch of raw market prices deterministically in input order."""

    return [convert_raw_to_observation(raw_price) for raw_price in raw_prices]


def build_enriched_observations(raw_prices: list[RawMarketPrice]) -> list[MarketObservation]:
    """Build chronologically ordered observations using only past market history."""

    history_by_instrument: dict[tuple[str, str | None, str | None, str | None], list[MarketPricePoint]] = {}
    observations: list[MarketObservation] = []

    for raw_price in _ordered_raw_prices(raw_prices):
        instrument_key = _instrument_key(raw_price)
        history: list[MarketPricePoint] = history_by_instrument.setdefault(instrument_key, [])
        observations.append(
            MarketObservation(
                asset_class=raw_price.asset_class,
                market_probability=raw_price.probability,
                reference_probability=_project_reference_probability(history, raw_price),
                liquidity_score=_liquidity_from_history(history),
                source=raw_price.source,
                event_id=raw_price.event_id,
                market_id=raw_price.market_id,
                selection_id=raw_price.selection_id,
                settled_outcome=raw_price.settled_outcome,
            )
        )
        history.append(
            MarketPricePoint(
                asset_class=raw_price.asset_class,
                probability=raw_price.probability,
                timestamp=raw_price.timestamp,
            )
        )

    return observations
