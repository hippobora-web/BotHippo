"""Public exports for the shared deterministic WINA decision core."""

from evengine.core.adapters import (
    decision_input_from_market_snapshot,
    decision_input_from_research_row,
)
from evengine.core.probability import (
    build_fair_value_estimate,
    clamp_probability,
    compute_edge,
)
from evengine.core.risk import (
    build_risk_decision,
    build_trade_intent,
    compute_recommended_size,
)
from evengine.core.signals import build_edge_signal, compute_signal_strength
from evengine.core.types import (
    DecisionInput,
    EdgeSignal,
    FairValueEstimate,
    RiskDecision,
    TradeIntent,
)

__all__ = [
    "DecisionInput",
    "EdgeSignal",
    "FairValueEstimate",
    "RiskDecision",
    "TradeIntent",
    "build_edge_signal",
    "build_fair_value_estimate",
    "build_risk_decision",
    "build_trade_intent",
    "clamp_probability",
    "compute_edge",
    "compute_recommended_size",
    "compute_signal_strength",
    "decision_input_from_market_snapshot",
    "decision_input_from_research_row",
]
