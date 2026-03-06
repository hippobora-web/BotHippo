"""Pydantic schemas for the paper-trading research lab."""

from __future__ import annotations

from typing import Union

from pydantic import BaseModel, Field


class StrategyIdea(BaseModel):
    """High-level research idea before specification and evaluation."""

    idea_id: str
    title: str
    hypothesis: str
    market_scope: str
    feature_scope: str
    rationale: str


class StrategySpec(BaseModel):
    """Versioned deterministic strategy specification stored in the local registry."""

    strategy_id: str
    version: str
    name: str
    params: dict[str, Union[float, int, str, bool]] = Field(default_factory=dict)
    enabled: int
    status: str


class BacktestMetrics(BaseModel):
    """Core paper-trading backtest metrics used for scoring and promotion decisions."""

    sample_size: int
    roi: float
    hit_rate: float
    avg_edge: float
    max_drawdown: float
    volatility: float
    stability_score: float


class StrategyEvaluation(BaseModel):
    """Deterministic evaluation outcome derived from backtest metrics."""

    strategy_id: str
    metrics: BacktestMetrics
    composite_score: float
    verdict: str
    reasons: list[str] = Field(default_factory=list)


class PromotionDecision(BaseModel):
    """Promotion gate for moving a strategy into paper-trading workflow only."""

    strategy_id: str
    promote_to_paper: int
    open_pr: int
    reject: int
    summary: str
