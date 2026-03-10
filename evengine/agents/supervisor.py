"""Supervisor orchestrator for the multi-agent pipeline."""

from __future__ import annotations

import logging

from evengine.agents.market_agent import process_market
from evengine.agents.research_agent import run_research
from evengine.agents.schemas import EventInput, MarketSnapshot


LOGGER = logging.getLogger(__name__)


def _market_snapshot_log_fields(snapshot: MarketSnapshot) -> dict[str, object]:
    """Build a small redacted summary for market snapshot logging."""

    return {
        "event_id": snapshot.event_id,
        "market_type": snapshot.market_type,
        "selection": snapshot.selection,
        "bookmaker": snapshot.bookmaker,
        "timestamp": snapshot.timestamp,
    }


def _research_log_fields(event: EventInput, raw_text: str) -> dict[str, object]:
    """Build a redacted summary for research output logging."""

    return {
        "event_id": event.event_id,
        "sport": event.sport,
        "competition": event.competition,
        "raw_text_chars": len(raw_text),
    }


def run_pipeline(event: EventInput) -> MarketSnapshot:
    """Run the minimal pipeline and return the market snapshot."""

    LOGGER.info(
        "supervisor pipeline started event_id=%s sport=%s market_type=%s",
        event.event_id,
        event.sport,
        event.market_type,
    )
    snapshot: MarketSnapshot = process_market(event)
    LOGGER.info("market agent completed %s", _market_snapshot_log_fields(snapshot))

    research_output = run_research(event)
    LOGGER.info(
        "research agent completed %s",
        _research_log_fields(event, research_output.raw_text),
    )

    return snapshot
