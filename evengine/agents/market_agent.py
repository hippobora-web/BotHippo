"""Market data normalization agent."""

from evengine.agents.schemas import EventInput, MarketSnapshot


def calculate_implied_probability(odds: float) -> float:
    """Compute implied probability from decimal odds."""

    if odds <= 0:
        raise ValueError("odds must be > 0")
    return 1.0 / odds


def process_market(event: EventInput) -> MarketSnapshot:
    """Transform raw market input into a normalized market snapshot."""

    implied_probability: float = calculate_implied_probability(event.odds)
    return MarketSnapshot(
        event_id=event.event_id,
        market_type=event.market_type,
        selection=event.selection,
        odds=event.odds,
        implied_probability=implied_probability,
        bookmaker=event.bookmaker,
        timestamp=event.timestamp,
    )
