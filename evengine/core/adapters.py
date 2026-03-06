"""Minimal adapters bridging external row formats into the shared decision core."""

from __future__ import annotations

from typing import Any

from evengine.core.types import DecisionInput


def _coerce_optional_float(value: Any, default: float | None = None) -> float | None:
    """Safely coerce a raw value to float, returning the provided default on failure."""

    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_optional_str(value: Any) -> str | None:
    """Safely coerce a raw value to a non-empty string."""

    if value is None:
        return None
    if isinstance(value, str):
        stripped: str = value.strip()
        return stripped if stripped else None
    return str(value)


def decision_input_from_market_snapshot(
    *,
    asset_class: str,
    source: str | None,
    event_id: str | None,
    market_id: str | None,
    selection_id: str | None,
    market_implied_probability: float | None,
    model_probability: float | None,
    confidence: float | None = None,
    liquidity_score: float | None = None,
    current_exposure: float | None = 0.0,
) -> DecisionInput:
    """Build a DecisionInput explicitly from market snapshot style fields."""

    return DecisionInput(
        asset_class=asset_class,
        source=source,
        event_id=event_id,
        market_id=market_id,
        selection_id=selection_id,
        market_implied_probability=market_implied_probability,
        model_probability=model_probability,
        confidence=confidence,
        liquidity_score=liquidity_score,
        current_exposure=current_exposure,
    )


def decision_input_from_research_row(row: dict) -> DecisionInput:
    """Build a generic DecisionInput from a dict-like research row."""

    return DecisionInput(
        asset_class=_coerce_optional_str(row.get("asset_class")) or "unknown",
        source=_coerce_optional_str(row.get("source")),
        event_id=_coerce_optional_str(row.get("event_id")),
        market_id=_coerce_optional_str(row.get("market_id")),
        selection_id=_coerce_optional_str(row.get("selection_id")),
        market_implied_probability=_coerce_optional_float(row.get("market_implied_probability")),
        model_probability=_coerce_optional_float(row.get("model_probability")),
        confidence=_coerce_optional_float(row.get("confidence")),
        liquidity_score=_coerce_optional_float(row.get("liquidity_score")),
        current_exposure=_coerce_optional_float(row.get("current_exposure"), 0.0),
    )
