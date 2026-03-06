"""Deterministic experiment tracking helpers."""

from __future__ import annotations

from evengine.experiment_tracking.types import ExperimentRun, ExperimentSummary


def record_experiment(
    run: ExperimentRun,
    history: list[ExperimentRun],
) -> list[ExperimentRun]:
    """Append one experiment run to an in-memory history."""

    return [*history, run]


def summarize_experiments(
    history: list[ExperimentRun],
) -> ExperimentSummary:
    """Summarize a run history and select the best run by total PnL."""

    best_run: ExperimentRun | None = None
    if history:
        best_run = max(
            history,
            key=lambda run: (
                run.total_pnl,
                run.win_rate,
                run.trades,
                -run.timestamp,
            ),
        )
    return ExperimentSummary(runs=list(history), best_run=best_run)
