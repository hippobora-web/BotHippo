"""Deterministic strategy scoring helpers for paper-trading research."""

from __future__ import annotations

from evengine.research_lab.schemas import BacktestMetrics, StrategyEvaluation


def clamp_score(value: float) -> float:
    """Clamp a numeric score into the closed interval [0.0, 1.0]."""

    return max(0.0, min(1.0, value))


def _normalize_roi(roi: float) -> float:
    """Normalize ROI into a bounded positive reward component."""

    return clamp_score(roi / 0.20)


def _normalize_hit_rate(hit_rate: float) -> float:
    """Normalize hit rate into a bounded reward component."""

    return clamp_score((hit_rate - 0.45) / 0.20)


def _normalize_avg_edge(avg_edge: float) -> float:
    """Normalize average edge into a bounded reward component."""

    return clamp_score(avg_edge / 0.10)


def _normalize_drawdown(max_drawdown: float) -> float:
    """Normalize drawdown into a bounded penalty component."""

    return clamp_score(max_drawdown / 0.30)


def _normalize_volatility(volatility: float) -> float:
    """Normalize volatility into a bounded penalty component."""

    return clamp_score(volatility / 0.30)


def compute_composite_score(metrics: BacktestMetrics) -> float:
    """Compute a deterministic composite score in the range [0.0, 1.0]."""

    roi_component: float = _normalize_roi(metrics.roi)
    hit_rate_component: float = _normalize_hit_rate(metrics.hit_rate)
    edge_component: float = _normalize_avg_edge(metrics.avg_edge)
    stability_component: float = clamp_score(metrics.stability_score)
    drawdown_component: float = 1.0 - _normalize_drawdown(metrics.max_drawdown)
    volatility_component: float = 1.0 - _normalize_volatility(metrics.volatility)

    score: float = (
        (0.25 * roi_component)
        + (0.20 * hit_rate_component)
        + (0.20 * edge_component)
        + (0.20 * stability_component)
        + (0.10 * drawdown_component)
        + (0.05 * volatility_component)
    )
    return clamp_score(score)


def evaluate_strategy(strategy_id: str, metrics: BacktestMetrics) -> StrategyEvaluation:
    """Evaluate a strategy deterministically from backtest metrics."""

    composite_score: float = compute_composite_score(metrics)
    reasons: list[str] = [
        f"sample_size={metrics.sample_size}",
        f"roi={metrics.roi:.4f}",
        f"hit_rate={metrics.hit_rate:.4f}",
        f"avg_edge={metrics.avg_edge:.4f}",
        f"max_drawdown={metrics.max_drawdown:.4f}",
        f"volatility={metrics.volatility:.4f}",
        f"stability_score={metrics.stability_score:.4f}",
        f"composite_score={composite_score:.4f}",
    ]

    if composite_score >= 0.70 and metrics.sample_size >= 300 and metrics.max_drawdown <= 0.15:
        verdict: str = "promote"
        reasons.append("verdict=promote because score, sample size, and drawdown gates passed")
    elif composite_score >= 0.55:
        verdict = "review"
        reasons.append("verdict=review because score cleared review threshold only")
    else:
        verdict = "reject"
        reasons.append("verdict=reject because score is below the review threshold")

    return StrategyEvaluation(
        strategy_id=strategy_id,
        metrics=metrics,
        composite_score=composite_score,
        verdict=verdict,
        reasons=reasons,
    )
