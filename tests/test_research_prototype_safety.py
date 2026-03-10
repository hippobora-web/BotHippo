"""Regression tests for the public-safe research prototype remediation pass."""

from __future__ import annotations

import unittest

from evengine.core.types import DecisionInput
from evengine.decision_pipeline import run_decision_pipeline
from evengine.live_adapters import RawMarketPrice, build_enriched_observations
from evengine.paper_trading.simulator import simulate_trade
from evengine.paper_trading.trade_types import TradeDecision


class ResearchPrototypeSafetyTests(unittest.TestCase):
    """Cover the highest-priority safety remediations."""

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

    def test_missing_critical_field_rejects(self) -> None:
        """Missing identifiers or decision inputs must reject instead of falling back."""

        result = run_decision_pipeline(
            DecisionInput(
                asset_class="soccer",
                source="book",
                event_id="event-1",
                market_id=None,
                selection_id="selection-1",
                market_implied_probability=0.40,
                model_probability=0.55,
                confidence=0.80,
                liquidity_score=0.75,
                current_exposure=0.0,
            )
        )

        self.assertFalse(result.risk_decision.approved)
        self.assertEqual(result.risk_decision.final_verdict, "reject")
        self.assertIn("market_id is required", result.risk_decision.reasons)

    def test_exposure_cap_uses_current_exposure_plus_proposed_size(self) -> None:
        """Approval must account for the new proposed trade size."""

        result = run_decision_pipeline(
            DecisionInput(
                asset_class="soccer",
                source="book",
                event_id="event-1",
                market_id="market-1",
                selection_id="selection-1",
                market_implied_probability=0.40,
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


if __name__ == "__main__":
    unittest.main()
