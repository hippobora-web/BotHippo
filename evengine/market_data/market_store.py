"""Simple deterministic JSONL storage for market snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evengine.market_data.types import MarketSelection, MarketSnapshot


SNAPSHOT_DIR: Path = Path("data/market_data/snapshots")
SNAPSHOT_FILE: Path = SNAPSHOT_DIR / "snapshots.jsonl"


def serialize_snapshot(snapshot: MarketSnapshot) -> dict[str, Any]:
    """Serialize a market snapshot into a JSON-safe dictionary."""

    return {
        "snapshot_id": snapshot.snapshot_id,
        "event_id": snapshot.event_id,
        "market_id": snapshot.market_id,
        "source": snapshot.source,
        "market_name": snapshot.market_name,
        "collected_at": snapshot.collected_at.isoformat(),
        "starts_at": snapshot.starts_at.isoformat() if snapshot.starts_at is not None else None,
        "overround": snapshot.overround,
        "selections": [
            {
                "selection_id": selection.selection_id,
                "label": selection.label,
                "odds": selection.odds,
                "price": selection.price,
                "implied_probability_raw": selection.implied_probability_raw,
                "implied_probability_fair": selection.implied_probability_fair,
            }
            for selection in snapshot.selections
        ],
    }


def deserialize_snapshot(payload: dict[str, Any]) -> MarketSnapshot:
    """Deserialize one JSON-safe dictionary into a MarketSnapshot object."""

    selections: list[MarketSelection] = [
        MarketSelection(
            selection_id=str(item["selection_id"]),
            label=str(item["label"]),
            odds=item.get("odds"),
            price=item.get("price"),
            implied_probability_raw=item.get("implied_probability_raw"),
            implied_probability_fair=item.get("implied_probability_fair"),
        )
        for item in payload.get("selections", [])
    ]
    return MarketSnapshot(
        snapshot_id=str(payload["snapshot_id"]),
        event_id=str(payload["event_id"]),
        market_id=str(payload["market_id"]),
        source=str(payload["source"]),
        market_name=str(payload["market_name"]),
        collected_at=__import__("datetime").datetime.fromisoformat(str(payload["collected_at"])),
        starts_at=(
            __import__("datetime").datetime.fromisoformat(str(payload["starts_at"]))
            if payload.get("starts_at") is not None
            else None
        ),
        selections=selections,
        overround=payload.get("overround"),
    )


def save_snapshot(snapshot: MarketSnapshot) -> None:
    """Append one market snapshot to the JSONL snapshot store."""

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    serialized: dict[str, Any] = serialize_snapshot(snapshot)
    with SNAPSHOT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(serialized, ensure_ascii=False) + "\n")


def load_snapshots() -> list[MarketSnapshot]:
    """Load all stored market snapshots from the JSONL snapshot directory."""

    if not SNAPSHOT_DIR.exists():
        return []

    snapshots: list[MarketSnapshot] = []
    for path in sorted(SNAPSHOT_DIR.glob("*.jsonl")):
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                stripped: str = line.strip()
                if not stripped:
                    continue
                payload: dict[str, Any] = json.loads(stripped)
                snapshots.append(deserialize_snapshot(payload))
    return snapshots
