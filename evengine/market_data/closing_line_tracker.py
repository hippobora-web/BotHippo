"""Deterministic helpers for latest and closing market line tracking."""

from __future__ import annotations

from evengine.market_data.types import MarketSelection, MarketSnapshot


def _matching_snapshots(
    snapshots: list[MarketSnapshot],
    *,
    event_id: str,
    market_id: str,
    source: str,
) -> list[MarketSnapshot]:
    """Return snapshots matching one market key, ordered by collection time ascending."""

    matched: list[MarketSnapshot] = [
        snapshot
        for snapshot in snapshots
        if snapshot.event_id == event_id
        and snapshot.market_id == market_id
        and snapshot.source == source
    ]
    return sorted(matched, key=lambda snapshot: snapshot.collected_at)


def get_latest_snapshot(
    snapshots: list[MarketSnapshot],
    *,
    event_id: str,
    market_id: str,
    source: str,
) -> MarketSnapshot | None:
    """Return the latest collected snapshot for one market key."""

    matched: list[MarketSnapshot] = _matching_snapshots(
        snapshots,
        event_id=event_id,
        market_id=market_id,
        source=source,
    )
    if not matched:
        return None
    return matched[-1]


def get_closing_snapshot(
    snapshots: list[MarketSnapshot],
    *,
    event_id: str,
    market_id: str,
    source: str,
) -> MarketSnapshot | None:
    """Return the last snapshot collected at or before market start time."""

    matched: list[MarketSnapshot] = _matching_snapshots(
        snapshots,
        event_id=event_id,
        market_id=market_id,
        source=source,
    )
    if not matched:
        return None
    starts_at = matched[0].starts_at
    if starts_at is None:
        return None

    closing_candidates: list[MarketSnapshot] = [
        snapshot for snapshot in matched if snapshot.starts_at is not None and snapshot.collected_at <= starts_at
    ]
    if not closing_candidates:
        return None
    return closing_candidates[-1]


def compute_decimal_clv(entry_odds: float, closing_odds: float) -> float:
    """Compute a simple decimal-odds closing line value delta."""

    return closing_odds - entry_odds


def _selection_map(snapshot: MarketSnapshot) -> dict[str, MarketSelection]:
    """Index selections by selection_id for deterministic comparison."""

    return {selection.selection_id: selection for selection in snapshot.selections}


def build_closing_line_summary(
    *,
    entry_snapshot: MarketSnapshot,
    closing_snapshot: MarketSnapshot,
) -> dict:
    """Build a small JSON-serializable summary comparing entry and closing lines."""

    entry_selections: dict[str, MarketSelection] = _selection_map(entry_snapshot)
    closing_selections: dict[str, MarketSelection] = _selection_map(closing_snapshot)
    compared_selection_ids: list[str] = sorted(
        selection_id
        for selection_id in entry_selections
        if selection_id in closing_selections
    )

    selection_summaries: list[dict] = []
    for selection_id in compared_selection_ids:
        entry_selection: MarketSelection = entry_selections[selection_id]
        closing_selection: MarketSelection = closing_selections[selection_id]
        item: dict = {
            "selection_id": selection_id,
            "label": entry_selection.label,
            "entry_odds": entry_selection.odds,
            "closing_odds": closing_selection.odds,
            "entry_raw_probability": entry_selection.implied_probability_raw,
            "closing_raw_probability": closing_selection.implied_probability_raw,
        }
        if entry_selection.odds is not None and closing_selection.odds is not None:
            item["decimal_clv"] = compute_decimal_clv(
                entry_selection.odds,
                closing_selection.odds,
            )
        selection_summaries.append(item)

    return {
        "event_id": entry_snapshot.event_id,
        "market_id": entry_snapshot.market_id,
        "source": entry_snapshot.source,
        "entry_collected_at": entry_snapshot.collected_at.isoformat(),
        "closing_collected_at": closing_snapshot.collected_at.isoformat(),
        "entry_overround": entry_snapshot.overround,
        "closing_overround": closing_snapshot.overround,
        "selections": selection_summaries,
    }
