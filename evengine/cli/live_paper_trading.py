"""CLI entrypoint for deterministic live paper trading."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from evengine.live_adapters import RawMarketPrice
from evengine.live_paper_trading import (
    LivePaperTradingInput,
    build_live_paper_trading_report,
    run_live_paper_trading,
)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the live paper trading CLI."""

    parser = argparse.ArgumentParser(description="Run deterministic live paper trading.")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON file containing raw market prices.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indentation for stdout output.",
    )
    parser.add_argument(
        "--current-exposure",
        type=float,
        default=0.0,
        help="Starting open exposure carried into the run.",
    )
    return parser.parse_args()


def _optional_bool(value: Any) -> bool | None:
    """Parse a nullable boolean value from JSON payloads."""

    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise ValueError("invalid_input_row")



def _load_raw_prices(path: str) -> list[RawMarketPrice]:
    """Load raw market prices from a JSON file into dataclass objects."""

    input_path: Path = Path(path)
    try:
        payload: Any = json.loads(input_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("input_file_not_found") from exc
    except OSError as exc:
        raise ValueError("input_file_unreadable") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_input_json") from exc

    if not isinstance(payload, list):
        raise ValueError("invalid_input_structure")

    raw_prices: list[RawMarketPrice] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError("invalid_input_row")
        try:
            raw_prices.append(
                RawMarketPrice(
                    asset_class=str(item["asset_class"]),
                    probability=float(item["probability"]),
                    timestamp=float(item["timestamp"]),
                    source=None if item.get("source") is None else str(item["source"]),
                    event_id=None if item.get("event_id") is None else str(item["event_id"]),
                    market_id=None if item.get("market_id") is None else str(item["market_id"]),
                    selection_id=(
                        None if item.get("selection_id") is None else str(item["selection_id"])
                    ),
                    settled_outcome=_optional_bool(item.get("settled_outcome")),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("invalid_input_row") from exc

    return raw_prices



def _build_summary(report) -> dict[str, Any]:
    """Build a JSON-serializable summary from a live paper trading report."""

    return asdict(report)



def main() -> int:
    """Run the live paper trading CLI and return a process exit code."""

    args = _parse_args()

    try:
        raw_prices: list[RawMarketPrice] = _load_raw_prices(args.input)
    except Exception as exc:
        print(
            json.dumps(
                {"error": str(exc), "stage": "input_loader"},
                ensure_ascii=False,
                indent=args.indent,
            )
        )
        return 2

    if not raw_prices:
        print(
            json.dumps(
                {
                    "error": "no_prices_loaded",
                    "stage": "input_loader",
                },
                ensure_ascii=False,
                indent=args.indent,
            )
        )
        return 1

    try:
        run = run_live_paper_trading(
            LivePaperTradingInput(
                raw_prices=raw_prices,
                current_exposure=args.current_exposure,
            )
        )
        report = build_live_paper_trading_report(run)
    except Exception as exc:
        print(
            json.dumps(
                {"error": str(exc), "stage": "live_paper_trading"},
                ensure_ascii=False,
                indent=args.indent,
            )
        )
        return 2

    print(json.dumps(_build_summary(report), ensure_ascii=False, indent=args.indent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
