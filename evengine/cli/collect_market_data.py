"""CLI entrypoint for deterministic market snapshot collection."""

from __future__ import annotations

import argparse
import json
from typing import Any

from evengine.market_data.adapters.mock_adapter import MockMarketAdapter
from evengine.market_data.market_collector import collect_and_store_market_snapshots
from evengine.market_data.types import MarketSnapshot


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the market data collector CLI."""

    parser = argparse.ArgumentParser(description="Collect deterministic market data snapshots.")
    parser.add_argument(
        "--adapter",
        default="mock",
        help="Adapter name to use for collection.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1,
        help="Number of collection iterations to run.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation for stdout output.",
    )
    return parser.parse_args()


def _load_adapter(adapter_name: str):
    """Load a deterministic market data adapter by name."""

    if adapter_name == "mock":
        return MockMarketAdapter()
    raise ValueError(f"unsupported_adapter:{adapter_name}")


def _build_summary(
    *,
    adapter_name: str,
    collections: int,
    snapshots_collected: int,
) -> dict[str, Any]:
    """Build the deterministic JSON summary returned by the CLI."""

    return {
        "adapter": adapter_name,
        "collections": collections,
        "snapshots_collected": snapshots_collected,
        "stored": True,
    }


def main() -> int:
    """Run the market data collector CLI and return a process exit code."""

    args = _parse_args()
    iterations: int = max(0, args.n)

    try:
        adapter = _load_adapter(args.adapter)
        total_snapshots: int = 0
        for _ in range(iterations):
            snapshots: list[MarketSnapshot] = collect_and_store_market_snapshots(adapter)
            total_snapshots += len(snapshots)
    except Exception as exc:
        print(
            json.dumps(
                {"error": str(exc), "stage": "market_collection"},
                ensure_ascii=False,
                indent=args.indent,
            )
        )
        return 2

    summary: dict[str, Any] = _build_summary(
        adapter_name=args.adapter,
        collections=iterations,
        snapshots_collected=total_snapshots,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=args.indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
