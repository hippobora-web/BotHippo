"""Regression tests for the public-safe research prototype remediation pass."""

from __future__ import annotations

import unittest

from evengine.core.types import DecisionInput
from evengine.decision_pipeline import run_decision_pipeline
from evengine.live_paper_trading import run_live_paper_trading
from evengine.live_paper_trading.types import LivePaperTradingInput
from evengine.live_adapters import RawMarketPrice, build_enriched_observations
from evengine.paper_trading.simulator import simulate_trade
from evengine.paper_trading.trade_types import TradeDecision
from evengine.pipeline.decision_pipeline import run_decision_pipeline as run_legacy_decision_pipeline
from evengine.pipeline.decision_types import DecisionInput as LegacyDecisionInput
from evengine.trade_execution_sim import execute_trade_intent, simulate_trade_outcome


class ResearchPrototypeSafetyTests(unittest.TestCase):
    """Cover the highest-priority safety remediations."""

    def _shared_decision_input(self, **overrides: object) -> DecisionInput:
        """Build a valid shared decision input with per-test overrides."""

        payload: dict[str, object] = {
            "asset_class": "soccer",
            "source": "book",
            "event_id": "event-1",
            "market_id": "market-1",
            "selection_id": "selection-1",
            "market_implied_probability": 0.40,
            "model_probability": 0.55,
            "confidence": 0.80,
            "liquidity_score": 0.75,
            "current_exposure": 0.0,
        }
        payload.update(overrides)
        return DecisionInput(**payload)

    def _legacy_decision_input(self, **overrides: object) -> LegacyDecisionInput:
        """Build a valid legacy decision input with per-test overrides."""

        payload: dict[str, object] = {
            "asset_class": "soccer",
            "source": "book",
            "event_id": "event-1",
            "market_id": "market-1",
            "selection_id": "selection-1",
            "market_implied_probability": 0.40,
            "model_probability": 0.55,
            "confidence": 0.80,
            "liquidity_score": 0.75,
            "current_exposure": 0.0,
        }
        payload.update(overrides)
        return LegacyDecisionInput(**payload)

    def test_enriched_observations_do_not_use_future_prices(self) -> None:
        """Earlier observations must not be influenced by later prices."""

        observations = build_enriched_observations(
            [
                RawMarketPrice(
                    asset_class="soccer",
                    probability=0.40,
                    timestamp=1.0,
                    source="book",
                    event_id="event-1",
                    market_id="market-1",
                    selection_id="selection-1",
                ),
                RawMarketPrice(
                    asset_class="soccer",
                    probability=0.90,
                    timestamp=2.0,
                    source="book",
                    event_id="event-1",
                    market_id="market-1",
                    selection_id="selection-1",
                ),
                RawMarketPrice(
                    asset_class="soccer",
                    probability=0.30,
                    timestamp=3.0,
                    source="book",
                    event_id="event-1",
                    market_id="market-1",
                    selection_id="selection-1",
                ),
            ]
        )

        self.assertEqual(len(observations), 3)
        self.assertAlmostEqual(observations[0].reference_probability, 0.40)
        self.assertAlmostEqual(observations[1].reference_probability, 0.40)
        self.assertAlmostEqual(observations[2].reference_probability, 0.90)

    def test_enriched_observations_are_chronological_and_isolated_per_instrument(self) -> None:
        """Chronological enrichment must not leak price history across instruments."""

        observations = build_enriched_observations(
            [
                RawMarketPrice(
                    asset_class="soccer",
                    probability=0.30,
                    timestamp=4.0,
                    source="book",
                    event_id="event-1",
                    market_id="market-1",
                    selection_id="selection-1",
                ),
                RawMarketPrice(
                    asset_class="tennis",
                    probability=0.60,
                    timestamp=1.0,
                    source="book",
                    event_id="event-2",
                    market_id="market-2",
                    selection_id="selection-2",
                ),
                RawMarketPrice(
                    asset_class="soccer",
                    probability=0.40,
                    timestamp=1.0,
                    source="book",
                    event_id="event-1",
                    market_id="market-1",
                    selection_id="selection-1",
                ),
                RawMarketPrice(
                    asset_class="soccer",
                    probability=0.90,
                    timestamp=2.0,
                    source="book",
                    event_id="event-1",
                    market_id="market-1",
                    selection_id="selection-1",
                ),
            ]
        )

        self.assertEqual(
            [observation.market_probability for observation in observations],
            [0.60, 0.40, 0.90, 0.30],
        )
        self.assertEqual(
            [observation.reference_probability for observation in observations],
            [0.60, 0.40, 0.40, 0.90],
        )

    def test_missing_critical_fields_reject_in_shared_and_legacy_pipelines(self) -> None:
        """Missing identifiers and inputs must reject consistently across pipeline entrypoints."""

        cases: tuple[tuple[str, object, str], ...] = (
            ("market_id", None, "market_id is required"),
            ("selection_id", None, "selection_id is required"),
            ("confidence", None, "confidence is required"),
            ("liquidity_score", None, "liquidity_score is required"),
            ("market_implied_probability", None, "market_implied_probability is required"),
        )

        for field_name, value, reason in cases:
            with self.subTest(field_name=field_name):
                shared_result = run_decision_pipeline(
                    self._shared_decision_input(**{field_name: value})
                )
                legacy_result = run_legacy_decision_pipeline(
                    self._legacy_decision_input(**{field_name: value})
                )

                self.assertFalse(shared_result.risk_decision.approved)
                self.assertEqual(shared_result.risk_decision.final_verdict, "reject")
                self.assertIn(reason, shared_result.risk_decision.reasons)

                self.assertFalse(legacy_result.approved)
                self.assertEqual(legacy_result.risk_verdict, "reject")
                self.assertIn(reason, legacy_result.reasons)

    def test_exposure_cap_uses_current_exposure_plus_proposed_size(self) -> None:
        """Approval must account for the new proposed trade size."""

        result = run_decision_pipeline(
            self._shared_decision_input(
                model_probability=0.80,
                confidence=0.90,
                liquidity_score=0.90,
                current_exposure=4.90,
            )
        )

        self.assertFalse(result.risk_decision.approved)
        self.assertEqual(result.risk_decision.final_verdict, "reject")
        self.assertTrue(
            any("current exposure plus proposed size exceeds" in reason for reason in result.risk_decision.reasons)
        )

    def test_paper_trading_pnl_is_odds_aware(self) -> None:
        """Settled wins and losses must use decimal-odds payouts, not flat +/- size."""

        winning_trade = simulate_trade(
            TradeDecision(
                asset_class="soccer",
                decision="bet",
                size=10.0,
                edge=0.05,
                entry_probability=0.25,
            ),
            True,
        )
        losing_trade = simulate_trade(
            TradeDecision(
                asset_class="soccer",
                decision="bet",
                size=10.0,
                edge=0.05,
                entry_probability=0.25,
            ),
            False,
        )

        self.assertAlmostEqual(winning_trade.entry_odds or 0.0, 4.0)
        self.assertAlmostEqual(winning_trade.pnl, 30.0)
        self.assertAlmostEqual(losing_trade.pnl, -10.0)

    def test_settlement_aware_trade_execution_realizes_pnl_only_when_settled(self) -> None:
        """Execution simulation must not realize synthetic PnL before settlement is known."""

        decision_result = run_decision_pipeline(
            self._shared_decision_input(
                market_implied_probability=0.25,
                model_probability=0.75,
                confidence=0.80,
                liquidity_score=0.90,
            )
        )
        simulated_trade = execute_trade_intent(decision_result.trade_intent)

        unsettled_pnl = simulate_trade_outcome(simulated_trade, None)
        settled_pnl = simulate_trade_outcome(simulated_trade, True)

        self.assertTrue(simulated_trade.executed)
        self.assertFalse(unsettled_pnl.settled)
        self.assertIsNone(unsettled_pnl.outcome)
        self.assertAlmostEqual(unsettled_pnl.pnl, 0.0)
        self.assertTrue(settled_pnl.settled)
        self.assertTrue(settled_pnl.outcome)
        self.assertAlmostEqual(settled_pnl.pnl, simulated_trade.size * 3.0)

    def test_live_paper_trading_does_not_realize_unsettled_trades(self) -> None:
        """The live batch runner must keep unresolved trades out of realized PnL."""

        run = run_live_paper_trading(
            LivePaperTradingInput(
                raw_prices=[
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
                        settled_outcome=None,
                    ),
                ]
            )
        )

        self.assertEqual(run.trades_executed, 1)
        self.assertEqual(run.trades_settled, 0)
        self.assertEqual(run.total_pnl, 0.0)
        self.assertEqual(run.pnl_history, [])


if __name__ == "__main__":
    unittest.main()
