"""Deterministic bridge from research rows to the shared decision pipeline."""

from __future__ import annotations

from evengine.decision_pipeline import (
    PipelineConfig,
    PipelineResult,
    run_pipeline_from_research_row,
)
from evengine.research_pipeline.types import ResearchPipelineResult


def run_research_pipeline_row(
    row: dict,
    *,
    config: PipelineConfig | None = None,
) -> ResearchPipelineResult:
    """Run the shared decision pipeline on one research row and expose bridge fields."""

    pipeline_result: PipelineResult = run_pipeline_from_research_row(row, config=config)
    trade_intent = pipeline_result.trade_intent
    return ResearchPipelineResult(
        input_row=dict(row),
        pipeline_result=pipeline_result,
        decision_verdict=trade_intent.action,
        approved=trade_intent.approved,
        recommended_size=trade_intent.size,
        edge=trade_intent.edge,
        reasons=list(trade_intent.reasons),
    )


def run_research_pipeline_dataset(
    rows: list[dict],
    *,
    config: PipelineConfig | None = None,
) -> list[ResearchPipelineResult]:
    """Run the research bridge over a deterministic ordered dataset."""

    return [run_research_pipeline_row(row, config=config) for row in rows]


def summarize_research_pipeline_results(
    results: list[ResearchPipelineResult],
) -> dict:
    """Build a small deterministic summary for bridge outputs."""

    valid_edges: list[float] = [result.edge for result in results if result.edge is not None]
    n_approved: int = sum(1 for result in results if result.approved)
    n_rejected: int = sum(
        1
        for result in results
        if result.decision_verdict == "hold" and (result.edge is None or result.edge <= 0.0)
    )
    n_watch: int = sum(
        1
        for result in results
        if result.decision_verdict == "hold" and result.edge is not None and result.edge > 0.0 and not result.approved
    )
    average_edge: float = sum(valid_edges) / len(valid_edges) if valid_edges else 0.0
    average_size: float = (
        sum(result.recommended_size for result in results) / len(results) if results else 0.0
    )
    return {
        "n_rows": len(results),
        "n_approved": n_approved,
        "n_rejected": n_rejected,
        "n_watch": n_watch,
        "average_edge": average_edge,
        "average_size": average_size,
    }
