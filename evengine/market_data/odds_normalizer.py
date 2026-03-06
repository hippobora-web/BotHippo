"""Pure deterministic helpers for converting odds into normalized probabilities."""

from __future__ import annotations

from dataclasses import replace

from evengine.market_data.types import MarketSelection


def decimal_to_implied_probability(odds: float) -> float:
    """Convert decimal odds into implied probability."""

    if odds <= 1.0:
        raise ValueError("decimal odds must be > 1.0")
    return 1.0 / odds


def american_to_implied_probability(odds: int) -> float:
    """Convert American odds into implied probability."""

    if odds == 0:
        raise ValueError("american odds must be non-zero")
    if odds > 0:
        return 100.0 / (odds + 100.0)
    absolute_odds: int = abs(odds)
    return absolute_odds / (absolute_odds + 100.0)


def _selection_raw_probability(selection: MarketSelection) -> float | None:
    """Resolve the best available raw implied probability for a selection."""

    if selection.implied_probability_raw is not None:
        return selection.implied_probability_raw
    if selection.odds is not None:
        return decimal_to_implied_probability(selection.odds)
    if selection.price is not None and 0.0 <= selection.price <= 1.0:
        return selection.price
    return None


def compute_overround(selections: list[MarketSelection]) -> float | None:
    """Compute market overround from available raw implied probabilities."""

    raw_probabilities: list[float] = []
    for selection in selections:
        probability: float | None = _selection_raw_probability(selection)
        if probability is not None:
            raw_probabilities.append(probability)
    if not raw_probabilities:
        return None
    return sum(raw_probabilities)


def remove_margin_proportional(selections: list[MarketSelection]) -> list[MarketSelection]:
    """Return new selections with fair probabilities computed by proportional margin removal."""

    overround: float | None = compute_overround(selections)
    normalized: list[MarketSelection] = []
    for selection in selections:
        raw_probability: float | None = _selection_raw_probability(selection)
        if raw_probability is None:
            normalized.append(replace(selection, implied_probability_raw=None, implied_probability_fair=None))
            continue
        if overround is None or overround <= 0.0:
            fair_probability: float = raw_probability
        else:
            fair_probability = raw_probability / overround
        normalized.append(
            replace(
                selection,
                implied_probability_raw=raw_probability,
                implied_probability_fair=fair_probability,
            )
        )
    return normalized


def normalize_market_probabilities(selections: list[MarketSelection]) -> list[MarketSelection]:
    """Normalize market selections by filling raw and fair implied probabilities."""

    return remove_margin_proportional(selections)
