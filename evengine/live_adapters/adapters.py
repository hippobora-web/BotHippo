"""Deterministic converters from raw market prices to scanner observations."""

from __future__ import annotations

from evengine.live_adapters.types import RawMarketPrice
from evengine.market_scanner.types import MarketObservation


def convert_raw_to_observation(raw: RawMarketPrice) -> MarketObservation:
    """Convert one raw market price into a market observation for scanning."""

    return MarketObservation(
        asset_class=raw.asset_class,
        market_probability=raw.probability,
        reference_probability=raw.probability,
        liquidity_score=None,
    )


def convert_batch(raw_prices: list[RawMarketPrice]) -> list[MarketObservation]:
    """Convert a batch of raw market prices deterministically in input order."""

    return [convert_raw_to_observation(raw_price) for raw_price in raw_prices]
