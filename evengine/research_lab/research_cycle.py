"""Deterministic end-to-end research cycle for the WINA paper-trading lab."""

from __future__ import annotations

from pathlib import Path

from evengine.research_lab.hyperopt import (
    build_optimized_strategy_spec,
    generate_param_candidates,
    optimize_strategy,
)
from evengine.research_lab.idea_generator import generate_strategy_ideas
from evengine.research_lab.promotion import decide_promotion
from evengine.research_lab.research_report_builder import (
    build_research_report,
    build_research_report_markdown,
    save_research_report_json,
    save_research_report_markdown,
)
from evengine.research_lab.schemas import PromotionDecision, StrategyEvaluation, StrategyIdea, StrategySpec
from evengine.research_lab.strategy_builder import build_strategy_from_idea
from evengine.research_lab.strategy_registry import upsert_strategy


def _report_paths(reports_dir: str, strategy_id: str) -> tuple[str, str]:
    """Build deterministic JSON and markdown report paths for one strategy."""

    reports_base: Path = Path(reports_dir)
    return (
        str(reports_base / f"{strategy_id}.json"),
        str(reports_base / f"{strategy_id}.md"),
    )


def _best_strategy_spec(
    *,
    base_strategy: StrategySpec,
    best_evaluation: StrategyEvaluation,
    candidates: list[StrategySpec],
) -> StrategySpec:
    """Recover the best candidate spec or fall back to the base strategy."""

    optimized_strategy: StrategySpec | None = build_optimized_strategy_spec(
        base_strategy,
        best_evaluation,
        candidates,
    )
    return optimized_strategy if optimized_strategy is not None else base_strategy


def _result_item(
    *,
    idea_id: str,
    strategy_spec: StrategySpec,
    evaluation: StrategyEvaluation,
    promotion_decision: PromotionDecision,
    report: dict,
) -> dict:
    """Build one deterministic research cycle result item."""

    return {
        "idea_id": idea_id,
        "strategy_id": strategy_spec.strategy_id,
        "version": strategy_spec.version,
        "composite_score": evaluation.composite_score,
        "verdict": evaluation.verdict,
        "promote_to_paper": promotion_decision.promote_to_paper,
        "open_pr": promotion_decision.open_pr,
        "reject": promotion_decision.reject,
        "report": report,
    }


def _error_result_item(idea: StrategyIdea, exc: Exception) -> dict:
    """Build a deterministic error result item for one failed research idea."""

    return {
        "idea_id": idea.idea_id,
        "strategy_id": "",
        "version": "",
        "composite_score": 0.0,
        "verdict": "error",
        "promote_to_paper": 0,
        "open_pr": 0,
        "reject": 1,
        "report": {
            "summary": f"research_cycle_error:{exc.__class__.__name__}"
        },
    }


def run_research_cycle(
    *,
    market_rows: list[dict],
    registry_path: str,
    reports_dir: str | None = None,
) -> list[dict]:
    """Run the full deterministic research pipeline across generated strategy ideas."""

    results: list[dict] = []

    for idea in generate_strategy_ideas():
        try:
            base_strategy: StrategySpec = build_strategy_from_idea(idea)
            candidates: list[StrategySpec] = generate_param_candidates(base_strategy)
            best_evaluation: StrategyEvaluation = optimize_strategy(base_strategy, market_rows)
            best_strategy_spec: StrategySpec = _best_strategy_spec(
                base_strategy=base_strategy,
                best_evaluation=best_evaluation,
                candidates=candidates,
            )
            promotion_decision: PromotionDecision = decide_promotion(best_evaluation)

            if promotion_decision.promote_to_paper == 1:
                upsert_strategy(registry_path, best_strategy_spec)

            report: dict = build_research_report(
                strategy_spec=best_strategy_spec,
                evaluation=best_evaluation,
                promotion_decision=promotion_decision,
            )
            markdown: str = build_research_report_markdown(
                strategy_spec=best_strategy_spec,
                evaluation=best_evaluation,
                promotion_decision=promotion_decision,
            )

            if reports_dir is not None:
                json_path, markdown_path = _report_paths(
                    reports_dir,
                    best_strategy_spec.strategy_id,
                )
                save_research_report_json(report=report, path=json_path)
                save_research_report_markdown(markdown=markdown, path=markdown_path)

            results.append(
                _result_item(
                    idea_id=idea.idea_id,
                    strategy_spec=best_strategy_spec,
                    evaluation=best_evaluation,
                    promotion_decision=promotion_decision,
                    report=report,
                )
            )
        except Exception as exc:
            results.append(_error_result_item(idea, exc))

    return results
