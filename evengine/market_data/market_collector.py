"""Deterministic collection helpers for market data adapters."""

from __future__ import annotations

from evengine.market_data.market_store import save_snapshot
from evengine.market_data.types import MarketSnapshot


def collect_market_snapshots(adapter) -> list[MarketSnapshot]:
    """Collect market snapshots from an adapter and validate their shape."""

    snapshots = adapter.fetch_market_snapshots()
    if not isinstance(snapshots, list):
        raise ValueError("adapter must return a list of MarketSnapshot")
    if not all(isinstance(snapshot, MarketSnapshot) for snapshot in snapshots):
        raise ValueError("adapter must return only MarketSnapshot objects")
    return snapshots


def collect_and_store_market_snapshots(adapter) -> list[MarketSnapshot]:
    """Collect market snapshots from an adapter and append them to storage."""

    snapshots: list[MarketSnapshot] = collect_market_snapshots(adapter)
    for snapshot in snapshots:
        save_snapshot(snapshot)
    return snapshots
