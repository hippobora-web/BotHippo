"""Deterministic quant agent placeholder for PR4 integration."""

from evengine.agents.quant_engine_adapter import (
    get_last_real_engine_status,
    run_real_quant_if_available,
)
from evengine.agents.schemas import (
    MarketSnapshot,
    QuantAgentMetadata,
    QuantDecision,
    QuantFeatures,
)


def _clamp_probability(value: float) -> float:
    """Clamp model probability to a safe closed interval."""

    return max(0.01, min(0.99, value))


def _bias_adjustment(qualitative_bias: str) -> float:
    """Return deterministic adjustment based on qualitative bias text."""

    normalized: str = qualitative_bias.lower().strip()
    positive_terms: tuple[str, ...] = (
        "positive",
        "supportive",
        "favorable",
        "favourable",
        "bullish",
        "home_positive",
    )
    negative_terms: tuple[str, ...] = (
        "negative",
        "against",
        "unfavorable",
        "unfavourable",
        "bearish",
        "home_negative",
    )

    if any(term in normalized for term in positive_terms):
        return 0.03
    if any(term in normalized for term in negative_terms):
        return -0.03
    return 0.0


def run_placeholder_quant(
    *,
    event_id: str,
    market_snapshot: MarketSnapshot,
    quant_features: QuantFeatures,
    fallback_reason: str,
) -> QuantDecision:
    """Compute deterministic placeholder quant decision from mapped features."""

    model_probability: float = market_snapshot.implied_probability
    model_probability += _bias_adjustment(quant_features.qualitative_bias)

    if quant_features.key_player_out == 1:
        model_probability -= 0.02
    if quant_features.lineup_uncertain == 1:
        model_probability -= 0.02
    if quant_features.rest_disadvantage == 1:
        model_probability -= 0.01
    if quant_features.motivation_boost == 1:
        model_probability += 0.01
    if quant_features.weather_risk == 1:
        model_probability -= 0.01
    if quant_features.info_uncertainty == 1:
        model_probability -= 0.02

    model_probability = _clamp_probability(model_probability)
    implied_probability: float = market_snapshot.implied_probability
    edge: float = model_probability - implied_probability
    ev: float = (market_snapshot.odds * model_probability) - 1.0

    if quant_features.info_uncertainty == 1 and quant_features.lineup_uncertain == 1:
        decision: str = "WATCH"
    elif edge >= 0.05 and ev > 0:
        decision = "BET"
    elif edge > 0:
        decision = "WATCH"
    else:
        decision = "REJECT"

    return QuantDecision(
        event_id=event_id,
        decision=decision,
        model_probability=model_probability,
        implied_probability=implied_probability,
        edge=edge,
        ev=ev,
        metadata=QuantAgentMetadata(
            engine_mode="placeholder",
            used_real_engine=0,
            fallback_reason=fallback_reason,
        ),
    )


def _fallback_reason_from_status(status: str) -> str:
    """Map adapter status to a stable placeholder fallback reason."""

    supported: set[str] = {
        "real_engine_disabled",
        "real_engine_native_unavailable",
        "real_engine_native_incompatible",
        "real_engine_import_unavailable",
        "real_engine_execution_failed",
        "real_engine_invalid_output",
    }
    if status in supported:
        return status
    return "real_engine_unavailable"


def run_quant(
    *,
    event_id: str,
    market_snapshot: MarketSnapshot,
    quant_features: QuantFeatures,
) -> QuantDecision:
    """Run real quant engine when available, otherwise use placeholder logic."""

    real_decision: QuantDecision | None = run_real_quant_if_available(
        event_id=event_id,
        market_snapshot=market_snapshot,
        quant_features=quant_features,
    )
    if real_decision is not None:
        if real_decision.metadata is None:
            real_decision = real_decision.model_copy(
                update={
                    "metadata": QuantAgentMetadata(
                        engine_mode="real",
                        used_real_engine=1,
                        fallback_reason="",
                    )
                }
            )
        return real_decision

    fallback_reason: str = _fallback_reason_from_status(get_last_real_engine_status())
    return run_placeholder_quant(
        event_id=event_id,
        market_snapshot=market_snapshot,
        quant_features=quant_features,
        fallback_reason=fallback_reason,
    )
