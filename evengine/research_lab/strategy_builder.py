"""Deterministic conversion from research ideas to executable strategy specs."""

from __future__ import annotations

import re

from evengine.research_lab.schemas import StrategyIdea, StrategySpec


_ODDS_RANGE_BY_SCOPE: dict[str, tuple[float, float]] = {
    "odds_low": (1.20, 1.79),
    "odds_mid": (1.80, 2.50),
    "odds_high": (2.51, 5.00),
}


def _extract_min_edge(title: str) -> float:
    """Extract the edge threshold from a deterministic strategy title."""

    match = re.search(r"edge\s*>=\s*(\d+)%", title, flags=re.IGNORECASE)
    if match is None:
        raise ValueError("unable to extract min_edge from strategy idea title")
    return int(match.group(1)) / 100.0


def _extract_market_scope(idea: StrategyIdea) -> str:
    """Extract or validate the market scope for the strategy idea."""

    if idea.market_scope in _ODDS_RANGE_BY_SCOPE:
        return idea.market_scope

    lowered_title: str = idea.title.lower()
    if "low odds" in lowered_title:
        return "odds_low"
    if "mid odds" in lowered_title:
        return "odds_mid"
    if "high odds" in lowered_title:
        return "odds_high"

    raise ValueError("unable to extract market scope from strategy idea")


def build_strategy_from_idea(idea: StrategyIdea) -> StrategySpec:
    """Build a deterministic executable strategy specification from an idea."""

    min_edge: float = _extract_min_edge(idea.title)
    market_scope: str = _extract_market_scope(idea)
    odds_min, odds_max = _ODDS_RANGE_BY_SCOPE[market_scope]

    return StrategySpec(
        strategy_id=f"strategy_{idea.idea_id}",
        version="v1",
        name=idea.title,
        params={
            "min_edge": min_edge,
            "odds_min": odds_min,
            "odds_max": odds_max,
        },
        enabled=1,
        status="candidate",
    )
