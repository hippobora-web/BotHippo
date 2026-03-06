"""Supervisor orchestrator for the multi-agent pipeline."""

from evengine.agents.market_agent import process_market
from evengine.agents.research_agent import run_research
from evengine.agents.schemas import EventInput, MarketSnapshot


def run_pipeline(event: EventInput) -> MarketSnapshot:
    """Run the minimal pipeline and return the market snapshot."""

    print("Supervisor: starting pipeline")
    snapshot: MarketSnapshot = process_market(event)
    print("Market agent completed")
    print(snapshot.model_dump())

    research_output = run_research(event)
    print("Research agent completed")
    print(research_output.model_dump())

    return snapshot
