"""Deterministic hyperparameter optimizer for the WINA research lab."""

from __future__ import annotations

from evengine.research_lab.backtest_runner import simulate_strategy
from evengine.research_lab.scorer import evaluate_strategy
from evengine.research_lab.schemas import StrategyEvaluation, StrategySpec


def _coerce_param_float(value: object, default: float) -> float:
    """Safely coerce a strategy parameter value to float."""

    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clamp_min_edge(value: float) -> float:
    """Clamp min_edge into the supported optimization range."""

    return max(0.0, min(0.20, value))


def _candidate_version(base_version: str, index: int) -> str:
    """Build a deterministic candidate version suffix."""

    return f"{base_version}-c{index:02d}"


def _candidate_key(params: dict[str, object]) -> tuple[float, float, float]:
    """Build a deterministic deduplication key for candidate parameters."""

    min_edge: float = round(_coerce_param_float(params.get("min_edge"), 0.0), 4)
    odds_min: float = round(_coerce_param_float(params.get("odds_min"), 1.01), 4)
    odds_max: float = round(_coerce_param_float(params.get("odds_max"), 10.0), 4)
    return (min_edge, odds_min, odds_max)


def generate_param_candidates(strategy_spec: StrategySpec) -> list[StrategySpec]:
    """Generate deterministic parameter candidates around a base strategy spec."""

    base_min_edge: float = _coerce_param_float(strategy_spec.params.get("min_edge"), 0.0)
    base_odds_min: float = _coerce_param_float(strategy_spec.params.get("odds_min"), 1.01)
    base_odds_max: float = _coerce_param_float(strategy_spec.params.get("odds_max"), 10.0)

    min_edge_values: list[float] = [
        _clamp_min_edge(base_min_edge - 0.01),
        _clamp_min_edge(base_min_edge),
        _clamp_min_edge(base_min_edge + 0.01),
        _clamp_min_edge(base_min_edge + 0.02),
    ]
    odds_min_values: list[float] = [
        max(1.01, round(base_odds_min - 0.10, 2)),
        round(base_odds_min, 2),
        round(base_odds_min + 0.10, 2),
    ]
    odds_max_values: list[float] = [
        round(base_odds_max - 0.10, 2),
        round(base_odds_max, 2),
        round(base_odds_max + 0.10, 2),
    ]

    candidates: list[StrategySpec] = []
    seen: set[tuple[float, float, float]] = set()

    for min_edge in min_edge_values:
        for odds_min in odds_min_values:
            for odds_max in odds_max_values:
                if odds_max <= odds_min:
                    continue
                if odds_max > 10.0:
                    continue

                params: dict[str, object] = dict(strategy_spec.params)
                params.update(
                    {
                        "min_edge": round(min_edge, 4),
                        "odds_min": round(odds_min, 2),
                        "odds_max": round(odds_max, 2),
                    }
                )
                dedupe_key: tuple[float, float, float] = _candidate_key(params)
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                candidates.append(
                    StrategySpec(
                        strategy_id=strategy_spec.strategy_id,
                        version="",
                        name=strategy_spec.name,
                        params=params,
                        enabled=strategy_spec.enabled,
                        status="candidate",
                    )
                )

    ordered_candidates: list[StrategySpec] = []
    for index, candidate in enumerate(candidates, start=1):
        ordered_candidates.append(
            candidate.model_copy(update={"version": _candidate_version(strategy_spec.version, index)})
        )
    return ordered_candidates


def _evaluation_sort_key(evaluation: StrategyEvaluation) -> tuple[float, int, float, str]:
    """Build deterministic sort key for candidate evaluation ranking."""

    return (
        evaluation.composite_score,
        evaluation.metrics.sample_size,
        -evaluation.metrics.max_drawdown,
        evaluation.strategy_id,
    )


def optimize_strategy(
    strategy_spec: StrategySpec,
    market_rows: list[dict],
) -> StrategyEvaluation:
    """Evaluate deterministic parameter candidates and return the best evaluation."""

    candidates: list[StrategySpec] = generate_param_candidates(strategy_spec)
    if not candidates:
        metrics = simulate_strategy(strategy_spec, market_rows)
        return evaluate_strategy(strategy_spec.strategy_id, metrics)

    evaluations: list[StrategyEvaluation] = []
    for candidate in candidates:
        metrics = simulate_strategy(candidate, market_rows)
        evaluations.append(
            evaluate_strategy(f"{candidate.strategy_id}:{candidate.version}", metrics)
        )

    return max(evaluations, key=_evaluation_sort_key)


def build_optimized_strategy_spec(
    strategy_spec: StrategySpec,
    best_evaluation: StrategyEvaluation,
    candidates: list[StrategySpec],
) -> StrategySpec | None:
    """Return the exact candidate spec matching the best evaluation."""

    target_strategy_id: str = best_evaluation.strategy_id
    for candidate in candidates:
        candidate_evaluation_id: str = f"{candidate.strategy_id}:{candidate.version}"
        if candidate_evaluation_id == target_strategy_id:
            return candidate
    return None
