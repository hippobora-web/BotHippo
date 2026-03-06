"""Dataclasses for bridging research rows into the shared decision pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field

from evengine.decision_pipeline.types import PipelineConfig, PipelineResult


@dataclass
class ResearchPipelineInput:
    """Input payload for evaluating one research row through the shared pipeline."""

    row: dict
    config: PipelineConfig | None = None


@dataclass
class ResearchPipelineResult:
    """Structured bridge result exposing research-friendly decision fields."""

    input_row: dict
    pipeline_result: PipelineResult
    decision_verdict: str
    approved: bool
    recommended_size: float
    edge: float | None
    reasons: list[str] = field(default_factory=list)
