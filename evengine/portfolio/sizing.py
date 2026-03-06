"""Deterministic stake sizing helpers."""

from __future__ import annotations


def compute_flat_stake(bankroll_eur: float, fraction: float) -> float:
    """Compute a flat stake from bankroll and fraction with safe rounding."""

    safe_bankroll: float = max(bankroll_eur, 0.0)
    safe_fraction: float = max(fraction, 0.0)
    stake: float = safe_bankroll * safe_fraction
    return round(max(stake, 0.0), 2)


def compute_capped_stake(
    bankroll_eur: float,
    proposed_fraction: float,
    cap_fraction: float,
) -> tuple[float, float]:
    """Compute capped stake and applied fraction, never returning negatives."""

    safe_proposed: float = max(proposed_fraction, 0.0)
    safe_cap: float = max(cap_fraction, 0.0)
    applied_fraction: float = min(safe_proposed, safe_cap)
    stake_eur: float = compute_flat_stake(bankroll_eur, applied_fraction)
    return stake_eur, applied_fraction

