"""Deterministic historical market data loader for the WINA research lab."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


_COLUMN_ALIASES: dict[str, tuple[str, ...]] = {
    "odds": ("odds", "price"),
    "implied_prob": ("implied_prob", "market_implied_prob", "market_prob"),
    "model_prob": ("model_prob", "fair_prob", "predicted_prob"),
    "result": ("result", "won", "outcome"),
}


def _load_json(path: str) -> list[dict]:
    """Load raw row dictionaries from a JSON file."""

    json_path: Path = Path(path)
    try:
        payload: Any = json.loads(json_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError("market_data_file_not_found") from exc
    except OSError as exc:
        raise ValueError("market_data_file_unreadable") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_market_data_json") from exc

    if isinstance(payload, list):
        if not all(isinstance(item, dict) for item in payload):
            raise ValueError("invalid_market_data_json_rows")
        return list(payload)

    if isinstance(payload, dict):
        rows: Any = payload.get("rows")
        if isinstance(rows, list) and all(isinstance(item, dict) for item in rows):
            return list(rows)

    raise ValueError("invalid_market_data_json_structure")


def _load_csv(path: str) -> list[dict]:
    """Load raw row dictionaries from a CSV file."""

    csv_path: Path = Path(path)
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise ValueError("invalid_market_data_csv_structure")
            return [dict(row) for row in reader]
    except FileNotFoundError as exc:
        raise ValueError("market_data_file_not_found") from exc
    except OSError as exc:
        raise ValueError("market_data_file_unreadable") from exc


def _coerce_float(value: Any) -> float | None:
    """Safely coerce a raw value into a float."""

    if value is None:
        return None
    if isinstance(value, str):
        stripped: str = value.strip()
        if not stripped:
            return None
        value = stripped
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_result(value: Any) -> int | None:
    """Safely coerce a raw result value into 0 or 1."""

    if isinstance(value, bool):
        return 1 if value else 0
    if isinstance(value, (int, float)) and value in {0, 1}:
        return int(value)
    if isinstance(value, str):
        normalized: str = value.strip().lower()
        if normalized in {"1", "true", "win", "won", "yes"}:
            return 1
        if normalized in {"0", "false", "loss", "lose", "lost", "no"}:
            return 0
    return None


def _first_present_value(row: dict, aliases: tuple[str, ...]) -> Any:
    """Return the first present value matching any accepted alias."""

    for alias in aliases:
        if alias in row:
            return row[alias]
    return None


def _normalize_row(row: dict) -> dict | None:
    """Normalize one raw market row into the strict research-lab row schema."""

    odds: float | None = _coerce_float(_first_present_value(row, _COLUMN_ALIASES["odds"]))
    implied_prob: float | None = _coerce_float(
        _first_present_value(row, _COLUMN_ALIASES["implied_prob"])
    )
    model_prob: float | None = _coerce_float(
        _first_present_value(row, _COLUMN_ALIASES["model_prob"])
    )
    result: int | None = _coerce_result(_first_present_value(row, _COLUMN_ALIASES["result"]))

    if odds is None or implied_prob is None or model_prob is None or result is None:
        return None
    if odds <= 1.0:
        return None
    if not 0.0 <= implied_prob <= 1.0:
        return None
    if not 0.0 <= model_prob <= 1.0:
        return None

    return {
        "odds": odds,
        "implied_prob": implied_prob,
        "model_prob": model_prob,
        "result": result,
    }


def load_market_rows(path: str) -> list[dict]:
    """Load and normalize historical market rows from JSON or CSV."""

    data_path: Path = Path(path)
    suffix: str = data_path.suffix.lower()
    if suffix == ".json":
        raw_rows: list[dict] = _load_json(path)
    elif suffix == ".csv":
        raw_rows = _load_csv(path)
    else:
        raise ValueError("unsupported_market_data_extension")

    normalized_rows: list[dict] = []
    for row in raw_rows:
        normalized_row: dict | None = _normalize_row(row)
        if normalized_row is not None:
            normalized_rows.append(normalized_row)
    return normalized_rows
