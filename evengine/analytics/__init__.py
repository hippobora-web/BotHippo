"""Public exports for deterministic analytics helpers."""

from evengine.analytics.metrics import (
    build_performance_report,
    compute_average_pnl,
    compute_pnl_variance,
)
from evengine.analytics.performance import (
    build_performance_summary,
    compute_average_clv,
    compute_average_edge,
    compute_hit_rate,
)
from evengine.analytics.types import PerformanceReport

__all__ = [
    "PerformanceReport",
    "build_performance_report",
    "build_performance_summary",
    "compute_average_clv",
    "compute_average_edge",
    "compute_average_pnl",
    "compute_hit_rate",
    "compute_pnl_variance",
]
