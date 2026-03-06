"""Dataclasses for deterministic live adapter inputs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RawMarketPrice:
    """One raw market price point converted by the local live adapter layer."""

    asset_class: str
    probability: float
    timestamp: float
