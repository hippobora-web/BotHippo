"""Deterministic analytics helpers for signal and CLV evaluation."""

from __future__ import annotations


def compute_hit_rate(outcomes: list[bool]) -> float:
    """Compute hit rate from boolean outcomes."""

    if not outcomes:
        return 0.0
    return sum(1 for outcome in outcomes if outcome) / len(outcomes)


def compute_average_edge(edges: list[float | None]) -> float:
    """Compute average edge while ignoring missing values."""

    valid_edges: list[float] = [edge for edge in edges if edge is not None]
    if not valid_edges:
        return 0.0
    return sum(valid_edges) / len(valid_edges)


def compute_average_clv(clvs: list[float | None]) -> float:
    """Compute average CLV while ignoring missing values."""

    valid_clvs: list[float] = [clv for clv in clvs if clv is not None]
    if not valid_clvs:
        return 0.0
    return sum(valid_clvs) / len(valid_clvs)


def build_performance_summary(
    *,
    outcomes: list[bool],
    edges: list[float | None],
    clvs: list[float | None],
) -> dict:
    """Build a deterministic summary of signal performance and CLV quality."""

    return {
        "n_outcomes": len(outcomes),
        "hit_rate": compute_hit_rate(outcomes),
        "average_edge": compute_average_edge(edges),
        "average_clv": compute_average_clv(clvs),
    }
