"""Bankroll configuration helpers."""

from __future__ import annotations

import os


def get_default_bankroll() -> float:
    """Return bankroll in EUR with safe env parsing and positive fallback."""

    raw_value: str | None = os.getenv("BANKROLL_EUR")
    if raw_value is None:
        return 100.0
    try:
        parsed: float = float(raw_value)
    except (TypeError, ValueError):
        return 100.0
    return parsed if parsed > 0 else 100.0

