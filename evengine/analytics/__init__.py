"""Public exports for deterministic analytics helpers."""

from evengine.analytics.performance import (
    build_performance_summary,
    compute_average_clv,
    compute_average_edge,
    compute_hit_rate,
)

__all__ = [
    "build_performance_summary",
    "compute_average_clv",
    "compute_average_edge",
    "compute_hit_rate",
]
