"""Deterministic dataset builder for market snapshot history."""

from __future__ import annotations

import json
from pathlib import Path

from evengine.market_data.closing_line_tracker import (
    get_closing_snapshot,
    get_latest_snapshot,
)
from evengine.market_data.market_store import load_snapshots
from evengine.market_data.types import MarketSnapshot


def load_all_snapshots() -> list[MarketSnapshot]:
    """Load all stored market snapshots in deterministic chronological order."""

    return sorted(load_snapshots(), key=lambda snapshot: snapshot.collected_at)


def group_snapshots_by_market(
    snapshots: list[MarketSnapshot],
) -> dict[tuple[str, str, str], list[MarketSnapshot]]:
    """Group snapshots by event_id, market_id, and source."""

    grouped: dict[tuple[str, str, str], list[MarketSnapshot]] = {}
    for snapshot in sorted(snapshots, key=lambda item: item.collected_at):
        key: tuple[str, str, str] = (
            snapshot.event_id,
            snapshot.market_id,
            snapshot.source,
        )
        grouped.setdefault(key, []).append(snapshot)
    return grouped


def build_feature_row(snapshots: list[MarketSnapshot]) -> dict:
    """Build one deterministic feature row from a market snapshot series."""

    if not snapshots:
        raise ValueError("snapshots must not be empty")

    ordered_snapshots: list[MarketSnapshot] = sorted(
        snapshots,
        key=lambda snapshot: snapshot.collected_at,
    )
    first_snapshot: MarketSnapshot = ordered_snapshots[0]
    latest_snapshot: MarketSnapshot | None = get_latest_snapshot(
        ordered_snapshots,
        event_id=first_snapshot.event_id,
        market_id=first_snapshot.market_id,
        source=first_snapshot.source,
    )
    closing_snapshot: MarketSnapshot | None = get_closing_snapshot(
        ordered_snapshots,
        event_id=first_snapshot.event_id,
        market_id=first_snapshot.market_id,
        source=first_snapshot.source,
    )

    start_time: str = ""
    if first_snapshot.starts_at is not None:
        start_time = first_snapshot.starts_at.isoformat()

    return {
        "event_id": first_snapshot.event_id,
        "market_id": first_snapshot.market_id,
        "source": first_snapshot.source,
        "start_time": start_time,
        "snapshot_count": len(ordered_snapshots),
        "latest_overround": None if latest_snapshot is None else latest_snapshot.overround,
        "closing_overround": None if closing_snapshot is None else closing_snapshot.overround,
        "has_closing_snapshot": closing_snapshot is not None,
    }


def build_market_dataset() -> list[dict]:
    """Build the full deterministic market dataset from stored snapshots."""

    snapshots: list[MarketSnapshot] = load_all_snapshots()
    grouped: dict[tuple[str, str, str], list[MarketSnapshot]] = group_snapshots_by_market(snapshots)
    dataset: list[dict] = []
    for key in sorted(grouped):
        dataset.append(build_feature_row(grouped[key]))
    return dataset


def export_dataset_json(path: str) -> None:
    """Export the built market dataset to a UTF-8 JSON file."""

    output_path: Path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataset: list[dict] = build_market_dataset()
    output_path.write_text(
        json.dumps(dataset, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
