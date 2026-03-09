"""Exposure stubs for PR9, to be replaced by real state/history integration."""

from __future__ import annotations


def get_stub_current_open_bets_count() -> int:
    """Return current open bets count placeholder (always zero in PR9)."""

    return 0


def get_stub_competition_exposure_fraction(competition: str) -> float:
    """Return competition exposure fraction placeholder (always zero in PR9)."""

    _ = competition
    return 0.0


def get_stub_daily_exposure_fraction() -> float:
    """Return daily exposure fraction placeholder (always zero in PR9)."""

    return 0.0

