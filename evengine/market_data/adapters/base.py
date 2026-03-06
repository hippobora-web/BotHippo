"""Abstract base adapter interface for market data collection."""

from __future__ import annotations

from abc import ABC, abstractmethod

from evengine.market_data.types import MarketSnapshot


class BaseMarketAdapter(ABC):
    """Abstract base class for deterministic market data adapters."""

    @abstractmethod
    def fetch_market_snapshots(self) -> list[MarketSnapshot]:
        """Return collected market snapshots for the adapter source."""
