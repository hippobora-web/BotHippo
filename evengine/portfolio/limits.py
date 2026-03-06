"""Portfolio risk limit helpers with deterministic env-driven defaults."""

from __future__ import annotations

import os


def _safe_fraction_env(name: str, default: float) -> float:
    """Read a non-negative fraction from environment with safe fallback."""

    raw_value: str | None = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed: float = float(raw_value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _safe_int_env(name: str, default: int) -> int:
    """Read a non-negative integer from environment with safe fallback."""

    raw_value: str | None = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed: int = int(raw_value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def max_bet_fraction() -> float:
    """Maximum fraction of bankroll allowed per single bet."""

    return _safe_fraction_env("MAX_BET_FRACTION", 0.02)


def max_daily_fraction() -> float:
    """Maximum fraction of bankroll allowed for daily exposure."""

    return _safe_fraction_env("MAX_DAILY_FRACTION", 0.10)


def max_open_bets() -> int:
    """Maximum number of simultaneous open bets."""

    return _safe_int_env("MAX_OPEN_BETS", 10)


def max_same_competition_exposure_fraction() -> float:
    """Maximum exposure fraction allowed on one competition."""

    return _safe_fraction_env("MAX_SAME_COMPETITION_EXPOSURE_FRACTION", 0.05)

