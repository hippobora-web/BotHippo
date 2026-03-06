"""Deterministic mock market adapter for local testing and pipeline development."""

from __future__ import annotations

from datetime import datetime, timezone

from evengine.market_data.adapters.base import BaseMarketAdapter
from evengine.market_data.odds_normalizer import compute_overround, normalize_market_probabilities
from evengine.market_data.types import MarketSelection, MarketSnapshot


class MockMarketAdapter(BaseMarketAdapter):
    """Deterministic mock adapter producing realistic soccer market snapshots."""

    def fetch_market_snapshots(self) -> list[MarketSnapshot]:
        """Return a small deterministic list of local mock market snapshots."""

        raw_selections: list[MarketSelection] = [
            MarketSelection(
                selection_id="sel_home",
                label="Home Win",
                odds=2.05,
            ),
            MarketSelection(
                selection_id="sel_draw",
                label="Draw",
                odds=3.35,
            ),
            MarketSelection(
                selection_id="sel_away",
                label="Away Win",
                odds=3.80,
            ),
        ]
        normalized_selections: list[MarketSelection] = normalize_market_probabilities(raw_selections)
        return [
            MarketSnapshot(
                snapshot_id="mock_snapshot_001",
                event_id="mock_event_psg_om_001",
                market_id="mock_market_1x2_001",
                source="mock_sportsbook",
                market_name="Match Result",
                collected_at=datetime(2026, 3, 6, 12, 0, 0, tzinfo=timezone.utc),
                starts_at=datetime(2026, 3, 7, 20, 0, 0, tzinfo=timezone.utc),
                selections=normalized_selections,
                overround=compute_overround(normalized_selections),
            )
        ]
