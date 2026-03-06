"""Public exports for the paper-trading research lab foundation."""

from evengine.research_lab.promotion import decide_promotion
from evengine.research_lab.scorer import clamp_score, compute_composite_score, evaluate_strategy
from evengine.research_lab.schemas import (
    BacktestMetrics,
    PromotionDecision,
    StrategyEvaluation,
    StrategyIdea,
    StrategySpec,
)
from evengine.research_lab.strategy_registry import (
    get_strategy,
    load_registry,
    save_registry,
    upsert_strategy,
)

__all__ = [
    "BacktestMetrics",
    "PromotionDecision",
    "StrategyEvaluation",
    "StrategyIdea",
    "StrategySpec",
    "clamp_score",
    "compute_composite_score",
    "decide_promotion",
    "evaluate_strategy",
    "get_strategy",
    "load_registry",
    "save_registry",
    "upsert_strategy",
]
