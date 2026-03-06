"""Public exports for deterministic simulated trade execution."""

from evengine.trade_execution_sim.executor import execute_trade_intent, simulate_trade_outcome
from evengine.trade_execution_sim.types import SimulatedTrade, TradePnL

__all__ = [
    "SimulatedTrade",
    "TradePnL",
    "execute_trade_intent",
    "simulate_trade_outcome",
]
