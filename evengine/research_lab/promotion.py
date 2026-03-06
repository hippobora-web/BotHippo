"""Promotion decisions for the paper-trading research lab."""

from __future__ import annotations

from evengine.research_lab.schemas import PromotionDecision, StrategyEvaluation


def decide_promotion(evaluation: StrategyEvaluation) -> PromotionDecision:
    """Map a strategy evaluation to a deterministic promotion decision."""

    if evaluation.verdict == "promote":
        return PromotionDecision(
            strategy_id=evaluation.strategy_id,
            promote_to_paper=1,
            open_pr=1,
            reject=0,
            summary="Promote strategy to paper-trading and open a PR for controlled rollout.",
        )

    if evaluation.verdict == "reject":
        return PromotionDecision(
            strategy_id=evaluation.strategy_id,
            promote_to_paper=0,
            open_pr=0,
            reject=1,
            summary="Reject strategy for now because evaluation did not clear paper-trading gates.",
        )

    return PromotionDecision(
        strategy_id=evaluation.strategy_id,
        promote_to_paper=0,
        open_pr=0,
        reject=0,
        summary="Keep strategy under review without opening a PR.",
    )
