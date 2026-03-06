"""Deterministic strategy configuration generator for research runs."""

from __future__ import annotations


def generate_strategies() -> list[dict]:
    """Generate deterministic research strategy configurations."""

    min_edge_thresholds: tuple[float, ...] = (0.01, 0.02, 0.03)
    min_confidences: tuple[float, ...] = (0.50, 0.70)
    min_liquidities: tuple[float, ...] = (0.30, 0.50)

    strategies: list[dict] = []
    index: int = 1
    for min_edge_threshold in min_edge_thresholds:
        for min_confidence in min_confidences:
            for min_liquidity in min_liquidities:
                strategies.append(
                    {
                        "strategy_id": f"research_strategy_{index:02d}",
                        "min_edge_threshold": min_edge_threshold,
                        "min_confidence": min_confidence,
                        "min_liquidity": min_liquidity,
                    }
                )
                index += 1
    return strategies
