"""Deterministic strategy idea generation for the WINA research lab."""

from __future__ import annotations

from evengine.research_lab.schemas import StrategyIdea


_EDGE_THRESHOLDS: tuple[float, ...] = (0.01, 0.02, 0.03, 0.05, 0.08)
_MARKET_FILTERS: tuple[str, ...] = ("odds_low", "odds_mid", "odds_high")
_MARKET_LABELS: dict[str, str] = {
    "odds_low": "low odds",
    "odds_mid": "mid odds",
    "odds_high": "high odds",
}
_MARKET_HYPOTHESES: dict[str, str] = {
    "odds_low": "odds between 1.20 and 1.79",
    "odds_mid": "odds between 1.80 and 2.50",
    "odds_high": "odds between 2.51 and 5.00",
}
_TARGET_COMBINATIONS: tuple[tuple[float, str], ...] = (
    (0.01, "odds_low"),
    (0.01, "odds_mid"),
    (0.02, "odds_low"),
    (0.02, "odds_mid"),
    (0.03, "odds_low"),
    (0.03, "odds_mid"),
    (0.03, "odds_high"),
    (0.05, "odds_mid"),
    (0.05, "odds_high"),
    (0.08, "odds_high"),
)


def _edge_percent(threshold: float) -> int:
    """Convert an edge threshold to an integer percentage."""

    return int(round(threshold * 100))


def _build_title(threshold: float, market_scope: str) -> str:
    """Build a deterministic strategy idea title."""

    return f"Edge >= {_edge_percent(threshold)}% in {_MARKET_LABELS[market_scope]}"


def _build_hypothesis(threshold: float, market_scope: str) -> str:
    """Build a deterministic strategy hypothesis."""

    return (
        f"Positive EV exists when model edge exceeds {_edge_percent(threshold)}% "
        f"for {_MARKET_HYPOTHESES[market_scope]}"
    )


def _build_rationale(threshold: float, market_scope: str) -> str:
    """Build a deterministic rationale for one strategy idea."""

    return (
        f"Test whether a minimum edge gate of {_edge_percent(threshold)}% "
        f"improves paper-trading quality inside the {market_scope} segment."
    )


def generate_strategy_ideas() -> list[StrategyIdea]:
    """Generate a deterministic bounded set of research strategy ideas."""

    ideas: list[StrategyIdea] = []
    for index, (threshold, market_scope) in enumerate(_TARGET_COMBINATIONS, start=1):
        if threshold not in _EDGE_THRESHOLDS or market_scope not in _MARKET_FILTERS:
            continue
        ideas.append(
            StrategyIdea(
                idea_id=f"idea_{index:03d}",
                title=_build_title(threshold, market_scope),
                hypothesis=_build_hypothesis(threshold, market_scope),
                market_scope=market_scope,
                feature_scope="edge",
                rationale=_build_rationale(threshold, market_scope),
            )
        )
    return ideas
