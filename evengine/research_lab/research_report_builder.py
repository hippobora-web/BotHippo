"""Deterministic research report builders for the WINA research lab."""

from __future__ import annotations

import json
from pathlib import Path

from evengine.research_lab.schemas import PromotionDecision, StrategyEvaluation, StrategySpec


def _format_float(value: float) -> str:
    """Format a float deterministically with four decimals."""

    return f"{value:.4f}"


def _metrics_dict(evaluation: StrategyEvaluation) -> dict:
    """Build the exact metrics dictionary expected in the JSON research report."""

    metrics = evaluation.metrics
    return {
        "sample_size": metrics.sample_size,
        "roi": metrics.roi,
        "hit_rate": metrics.hit_rate,
        "avg_edge": metrics.avg_edge,
        "max_drawdown": metrics.max_drawdown,
        "volatility": metrics.volatility,
        "stability_score": metrics.stability_score,
    }


def _promotion_dict(promotion_decision: PromotionDecision) -> dict:
    """Build the exact promotion decision dictionary expected in the report."""

    return {
        "promote_to_paper": promotion_decision.promote_to_paper,
        "open_pr": promotion_decision.open_pr,
        "reject": promotion_decision.reject,
        "summary": promotion_decision.summary,
    }


def _summary_text(
    strategy_spec: StrategySpec,
    evaluation: StrategyEvaluation,
    promotion_decision: PromotionDecision,
) -> str:
    """Build a short deterministic research summary sentence."""

    return (
        f"Strategy {strategy_spec.strategy_id} scored "
        f"{_format_float(evaluation.composite_score)} with "
        f"verdict={evaluation.verdict} and "
        f"promote_to_paper={promotion_decision.promote_to_paper}."
    )


def build_research_report(
    *,
    strategy_spec: StrategySpec,
    evaluation: StrategyEvaluation,
    promotion_decision: PromotionDecision,
) -> dict:
    """Build a deterministic JSON-serializable research report dictionary."""

    return {
        "strategy_id": strategy_spec.strategy_id,
        "version": strategy_spec.version,
        "name": strategy_spec.name,
        "params": strategy_spec.params,
        "metrics": _metrics_dict(evaluation),
        "composite_score": evaluation.composite_score,
        "verdict": evaluation.verdict,
        "promotion_decision": _promotion_dict(promotion_decision),
        "reasons": evaluation.reasons,
        "summary": _summary_text(strategy_spec, evaluation, promotion_decision),
    }


def build_research_report_markdown(
    *,
    strategy_spec: StrategySpec,
    evaluation: StrategyEvaluation,
    promotion_decision: PromotionDecision,
) -> str:
    """Build a deterministic plain-markdown research report."""

    metrics = evaluation.metrics
    lines: list[str] = [
        "# Research Report",
        "",
        "## Strategy",
        f"- strategy_id: {strategy_spec.strategy_id}",
        f"- version: {strategy_spec.version}",
        f"- name: {strategy_spec.name}",
        "",
        "## Parameters",
    ]

    if strategy_spec.params:
        for key in sorted(strategy_spec.params):
            value = strategy_spec.params[key]
            if isinstance(value, float):
                lines.append(f"- {key}: {_format_float(value)}")
            else:
                lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Metrics",
            f"- sample_size: {metrics.sample_size}",
            f"- roi: {_format_float(metrics.roi)}",
            f"- hit_rate: {_format_float(metrics.hit_rate)}",
            f"- avg_edge: {_format_float(metrics.avg_edge)}",
            f"- max_drawdown: {_format_float(metrics.max_drawdown)}",
            f"- volatility: {_format_float(metrics.volatility)}",
            f"- stability_score: {_format_float(metrics.stability_score)}",
            "",
            "## Evaluation",
            f"- composite_score: {_format_float(evaluation.composite_score)}",
            f"- verdict: {evaluation.verdict}",
            "",
            "## Promotion Decision",
            f"- promote_to_paper: {promotion_decision.promote_to_paper}",
            f"- open_pr: {promotion_decision.open_pr}",
            f"- reject: {promotion_decision.reject}",
            f"- summary: {promotion_decision.summary}",
            "",
            "## Reasons",
        ]
    )

    if evaluation.reasons:
        for reason in evaluation.reasons:
            lines.append(f"- {reason}")
    else:
        lines.append("- none")

    return "\n".join(lines)


def save_research_report_json(
    *,
    report: dict,
    path: str,
) -> None:
    """Persist a research report dictionary as UTF-8 JSON with trailing newline."""

    report_path: Path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def save_research_report_markdown(
    *,
    markdown: str,
    path: str,
) -> None:
    """Persist markdown research report content as UTF-8 text with trailing newline."""

    report_path: Path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(markdown.rstrip("\n") + "\n", encoding="utf-8")
