"""Dataclasses for the shared end-to-end decision pipeline."""

from __future__ import annotations

from dataclasses import dataclass

from evengine.core.types import DecisionInput, EdgeSignal, FairValueEstimate, RiskDecision, TradeIntent


@dataclass
class PipelineConfig:
    """Deterministic configuration for the shared decision pipeline."""

    min_edge: float = 0.02
    min_confidence: float = 0.50
    min_liquidity: float = 0.30
    max_position_size: float = 1.0
    max_total_exposure: float = 5.0


@dataclass
class PipelineResult:
    """Full end-to-end output bundle for one decision pipeline evaluation."""

    decision_input: DecisionInput
    fair_value: FairValueEstimate
    edge_signal: EdgeSignal
    risk_decision: RiskDecision
    trade_intent: TradeIntent
