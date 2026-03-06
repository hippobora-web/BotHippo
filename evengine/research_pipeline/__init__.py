"""Public exports for the deterministic research-to-decision bridge."""

from evengine.research_pipeline.bridge import (
    run_research_pipeline_dataset,
    run_research_pipeline_row,
    summarize_research_pipeline_results,
)
from evengine.research_pipeline.types import ResearchPipelineInput, ResearchPipelineResult

__all__ = [
    "ResearchPipelineInput",
    "ResearchPipelineResult",
    "run_research_pipeline_dataset",
    "run_research_pipeline_row",
    "summarize_research_pipeline_results",
]
