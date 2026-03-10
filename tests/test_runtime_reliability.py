"""Runtime reliability regression tests for persistence and state integrity."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import evengine.market_data.market_store as market_store
from evengine.agents.perplexity_client import _get_api_key, fetch_event_research
from evengine.agents.research_agent import run_research
from evengine.agents.schemas import EventInput
from evengine.live_adapters import RawMarketPrice
from evengine.market_data.types import MarketSelection, MarketSnapshot
from evengine.orchestrator import run_orchestrator
from evengine.orchestrator.types import OrchestratorInput


class MarketStoreReliabilityTests(unittest.TestCase):
    """Cover append-only JSONL persistence invariants."""

    def _snapshot(
        self,
        *,
        snapshot_id: str,
        event_id: str = "event-1",
        market_id: str = "market-1",
        source: str = "book",
        collected_at: datetime,
    ) -> MarketSnapshot:
        """Build one snapshot with a non-empty selection payload."""

        return MarketSnapshot(
            snapshot_id=snapshot_id,
            event_id=event_id,
            market_id=market_id,
            source=source,
            market_name="Match Odds",
            collected_at=collected_at,
            starts_at=datetime(2026, 3, 12, 18, 0, 0),
            selections=[
                MarketSelection(
                    selection_id="selection-1",
                    label="Home",
                    odds=2.5,
                    price=0.40,
                    implied_probability_raw=0.40,
                    implied_probability_fair=0.38,
                )
            ],
            overround=1.02,
        )

    def _patch_snapshot_store(self, snapshot_dir: Path) -> tuple[Path, object, object]:
        """Return patched snapshot-dir context managers for one temporary store."""

        snapshot_file = snapshot_dir / "snapshots.jsonl"
        return (
            snapshot_file,
            patch.object(market_store, "SNAPSHOT_DIR", snapshot_dir),
            patch.object(market_store, "SNAPSHOT_FILE", snapshot_file),
        )

    def test_save_and_load_snapshots_preserve_append_consistency(self) -> None:
        """Saved snapshots should round-trip through the JSONL store without field loss."""

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = Path(temp_dir)
            snapshot_file, patch_dir, patch_file = self._patch_snapshot_store(snapshot_dir)
            later_snapshot = self._snapshot(
                snapshot_id="snapshot-2",
                collected_at=datetime(2026, 3, 11, 12, 5, 0),
            )
            earlier_snapshot = self._snapshot(
                snapshot_id="snapshot-1",
                collected_at=datetime(2026, 3, 11, 12, 0, 0),
            )

            with patch_dir, patch_file:
                market_store.save_snapshot(later_snapshot)
                market_store.save_snapshot(earlier_snapshot)
                loaded = market_store.load_snapshots()

            self.assertTrue(snapshot_file.exists())
            self.assertEqual([snapshot.snapshot_id for snapshot in loaded], ["snapshot-2", "snapshot-1"])
            self.assertEqual(loaded[0].market_name, "Match Odds")
            self.assertEqual(len(loaded[0].selections), 1)
            self.assertAlmostEqual(loaded[0].selections[0].odds or 0.0, 2.5)
            self.assertAlmostEqual(loaded[0].overround or 0.0, 1.02)

    def test_load_snapshots_for_market_filters_and_sorts_chronologically(self) -> None:
        """Market-scoped loads should return only matching snapshots ordered by timestamp."""

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = Path(temp_dir)
            _, patch_dir, patch_file = self._patch_snapshot_store(snapshot_dir)

            with patch_dir, patch_file:
                market_store.save_snapshot(
                    self._snapshot(
                        snapshot_id="snapshot-2",
                        event_id="event-1",
                        market_id="market-1",
                        source="book",
                        collected_at=datetime(2026, 3, 11, 12, 5, 0),
                    )
                )
                market_store.save_snapshot(
                    self._snapshot(
                        snapshot_id="snapshot-3",
                        event_id="event-2",
                        market_id="market-2",
                        source="exchange",
                        collected_at=datetime(2026, 3, 11, 12, 1, 0),
                    )
                )
                market_store.save_snapshot(
                    self._snapshot(
                        snapshot_id="snapshot-1",
                        event_id="event-1",
                        market_id="market-1",
                        source="book",
                        collected_at=datetime(2026, 3, 11, 12, 0, 0),
                    )
                )

                loaded = market_store.load_snapshots_for_market(
                    event_id="event-1",
                    market_id="market-1",
                    source="book",
                )

            self.assertEqual([snapshot.snapshot_id for snapshot in loaded], ["snapshot-1", "snapshot-2"])

    def test_duplicate_snapshot_lines_are_loaded_as_distinct_records(self) -> None:
        """The append-only JSONL store currently preserves duplicate lines as separate records."""

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = Path(temp_dir)
            snapshot_file, patch_dir, patch_file = self._patch_snapshot_store(snapshot_dir)
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            payload = market_store.serialize_snapshot(
                self._snapshot(
                    snapshot_id="snapshot-duplicate",
                    collected_at=datetime(2026, 3, 11, 12, 0, 0),
                )
            )
            snapshot_file.write_text(
                json.dumps(payload) + "\n" + json.dumps(payload) + "\n",
                encoding="utf-8",
            )

            with patch_dir, patch_file:
                loaded = market_store.load_snapshots()

            self.assertEqual([snapshot.snapshot_id for snapshot in loaded], ["snapshot-duplicate", "snapshot-duplicate"])

    def test_malformed_snapshot_line_raises_json_decode_error(self) -> None:
        """Malformed JSONL lines should fail loudly instead of producing partial silent state."""

        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot_dir = Path(temp_dir)
            snapshot_file, patch_dir, patch_file = self._patch_snapshot_store(snapshot_dir)
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            snapshot_file.write_text("{not-json}\n", encoding="utf-8")

            with patch_dir, patch_file:
                with self.assertRaises(json.JSONDecodeError):
                    market_store.load_snapshots()


class ResearchClientReliabilityTests(unittest.TestCase):
    """Cover failure behavior for external research-fetch paths."""

    def _event(self) -> EventInput:
        """Build one valid event payload for research-agent tests."""

        return EventInput(
            event_id="event-1",
            sport="soccer",
            competition="Ligue 1",
            home_team="Home FC",
            away_team="Away FC",
            market_type="moneyline",
            selection="Home FC",
            odds=2.5,
            bookmaker="book",
            timestamp="2026-03-11T12:00:00",
        )

    def test_get_api_key_requires_environment_variable(self) -> None:
        """Client setup should fail clearly when the API key is missing."""

        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "PERPLEXITY_API_KEY"):
                _get_api_key()

    def test_fetch_event_research_rejects_unexpected_response_shape(self) -> None:
        """Malformed client responses should surface a deterministic validation error."""

        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {}

        with patch.dict("os.environ", {"PERPLEXITY_API_KEY": "test-key"}, clear=True):
            with patch("evengine.agents.perplexity_client.requests.post", return_value=response) as post:
                with self.assertRaisesRegex(ValueError, "Unexpected response format"):
                    fetch_event_research("prompt")

        post.assert_called_once()

    def test_run_research_returns_fallback_output_when_fetch_fails(self) -> None:
        """Research-agent failures should degrade to a structured empty result, not raise."""

        with patch(
            "evengine.agents.research_agent.fetch_event_research",
            side_effect=RuntimeError("network unavailable"),
        ):
            result = run_research(self._event())

        self.assertEqual(result.event_id, "event-1")
        self.assertEqual(result.uncertainty_flags, ["research_fetch_failed"])
        self.assertEqual(result.source_quality_score, 0.0)
        self.assertEqual(result.raw_text, "")
        self.assertEqual(result.injuries_summary, [])


class OrchestratorStateIntegrityTests(unittest.TestCase):
    """Cover longer end-to-end sequences where exposure transitions matter."""

    def _raw_sequence(
        self,
        *,
        first_outcome: bool | None,
        second_outcome: bool | None,
    ) -> list[RawMarketPrice]:
        """Build two independent anomaly sequences with deterministic timestamps."""

        return [
            RawMarketPrice(
                asset_class="soccer",
                probability=0.20,
                timestamp=1.0,
                source="book",
                event_id="event-1",
                market_id="market-1",
                selection_id="selection-1",
            ),
            RawMarketPrice(
                asset_class="soccer",
                probability=0.80,
                timestamp=2.0,
                source="book",
                event_id="event-1",
                market_id="market-1",
                selection_id="selection-1",
            ),
            RawMarketPrice(
                asset_class="soccer",
                probability=0.10,
                timestamp=3.0,
                source="book",
                event_id="event-1",
                market_id="market-1",
                selection_id="selection-1",
                settled_outcome=first_outcome,
            ),
            RawMarketPrice(
                asset_class="soccer",
                probability=0.20,
                timestamp=4.0,
                source="book",
                event_id="event-2",
                market_id="market-2",
                selection_id="selection-2",
            ),
            RawMarketPrice(
                asset_class="soccer",
                probability=0.80,
                timestamp=5.0,
                source="book",
                event_id="event-2",
                market_id="market-2",
                selection_id="selection-2",
            ),
            RawMarketPrice(
                asset_class="soccer",
                probability=0.10,
                timestamp=6.0,
                source="book",
                event_id="event-2",
                market_id="market-2",
                selection_id="selection-2",
                settled_outcome=second_outcome,
            ),
        ]

    def test_orchestrator_carries_unsettled_exposure_into_later_anomalies(self) -> None:
        """An unsettled executed trade should keep consuming exposure in the same pass."""

        result = run_orchestrator(
            OrchestratorInput(
                raw_prices=self._raw_sequence(first_outcome=None, second_outcome=None),
                current_exposure=4.5,
            )
        )

        self.assertEqual(result.anomalies_detected, 4)
        self.assertEqual(result.trades_executed, 1)
        self.assertEqual(result.total_pnl, 0.0)

    def test_orchestrator_releases_exposure_after_settlement(self) -> None:
        """A settled trade should free exposure before the next anomaly is evaluated."""

        result = run_orchestrator(
            OrchestratorInput(
                raw_prices=self._raw_sequence(first_outcome=True, second_outcome=None),
                current_exposure=4.5,
            )
        )

        expected_first_trade_size = 0.70 * 0.70 * 0.91
        expected_first_trade_pnl = expected_first_trade_size * 9.0

        self.assertEqual(result.anomalies_detected, 4)
        self.assertEqual(result.trades_executed, 2)
        self.assertAlmostEqual(result.total_pnl, expected_first_trade_pnl)


if __name__ == "__main__":
    unittest.main()
