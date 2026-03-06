"""Public exports for generic edge-signal construction."""

from evengine.signals.edge_engine import build_edge_signal, compute_signal_strength
from evengine.signals.types import EdgeSignal

__all__ = [
    "EdgeSignal",
    "build_edge_signal",
    "compute_signal_strength",
]
