"""Universe agent for deterministic candidate scoring and ranking."""

from __future__ import annotations

from evengine.agents.schemas import EventInput, UniverseCandidate


_PREFERRED_MARKETS: set[str] = {"1x2", "moneyline", "over_under"}


def _build_candidate_flags(event_input: EventInput) -> list[str]:
    """Build deterministic candidate flags from event attributes."""

    flags: list[str] = []
    sport: str = event_input.sport.strip().lower()
    market_type: str = event_input.market_type.strip().lower()
    bookmaker: str = event_input.bookmaker.strip()

    if sport == "football":
        flags.append("preferred_sport")
    if market_type in _PREFERRED_MARKETS:
        flags.append("preferred_market")
    if 1.5 <= event_input.odds <= 3.5:
        flags.append("midrange_odds")
    if not bookmaker:
        flags.append("missing_bookmaker")

    return flags


def score_candidate(event_input: EventInput) -> float:
    """Score one candidate event/market with deterministic PR9 rules."""

    score: float = 0.0
    sport: str = event_input.sport.strip().lower()
    market_type: str = event_input.market_type.strip().lower()
    bookmaker: str = event_input.bookmaker.strip()

    if sport == "football":
        score += 1.0
    if market_type in _PREFERRED_MARKETS:
        score += 0.5
    if 1.5 <= event_input.odds <= 3.5:
        score += 0.25
    if not bookmaker:
        score -= 0.5

    return score


def build_universe_candidate(event_input: EventInput) -> UniverseCandidate:
    """Create one UniverseCandidate from EventInput."""

    return UniverseCandidate(
        event_id=event_input.event_id,
        sport=event_input.sport,
        competition=event_input.competition,
        home_team=event_input.home_team,
        away_team=event_input.away_team,
        market_type=event_input.market_type,
        selection=event_input.selection,
        bookmaker=event_input.bookmaker,
        odds=event_input.odds,
        timestamp=event_input.timestamp,
        priority_score=score_candidate(event_input),
        candidate_flags=_build_candidate_flags(event_input),
    )


def rank_candidates(candidates: list[UniverseCandidate]) -> list[UniverseCandidate]:
    """Return candidates sorted by descending priority score."""

    return sorted(candidates, key=lambda candidate: candidate.priority_score, reverse=True)

