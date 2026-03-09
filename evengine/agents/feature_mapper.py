"""Feature mapper converting agent outputs into quant-ready features."""

from evengine.agents.schemas import AnalysisOutput, QuantFeatures, ResearchOutput


def _contains_any(text_items: list[str], terms: tuple[str, ...]) -> bool:
    """Return True when any term appears in any text item."""

    lowered_items: list[str] = [item.lower() for item in text_items]
    lowered_terms: list[str] = [term.lower() for term in terms]
    return any(term in item for item in lowered_items for term in lowered_terms)


def _to_flag(value: bool) -> int:
    """Convert boolean condition to deterministic binary feature."""

    return 1 if value else 0


def map_to_quant_features(
    *,
    event_id: str,
    research_output: ResearchOutput,
    analysis_output: AnalysisOutput,
) -> QuantFeatures:
    """Map research and analysis outputs to deterministic quant features."""

    key_player_out_terms: tuple[str, ...] = ("key", "star", "captain", "starting goalkeeper")
    lineup_uncertain_terms: tuple[str, ...] = (
        "lineup",
        "lineups",
        "composition",
        "compositions",
        "unconfirmed",
        "unknown",
        "not confirmed",
    )
    rest_disadvantage_terms: tuple[str, ...] = ("played 3 days ago", "short rest", "fatigue")
    motivation_boost_terms: tuple[str, ...] = (
        "must win",
        "qualification",
        "title race",
        "relegation battle",
    )
    weather_risk_terms: tuple[str, ...] = ("rain", "wind", "storm", "snow")

    key_player_out: int = _to_flag(
        _contains_any(research_output.injuries_summary, key_player_out_terms)
    )
    lineup_uncertain: int = _to_flag(
        _contains_any(research_output.uncertainty_flags, lineup_uncertain_terms)
    )
    rest_disadvantage: int = _to_flag(
        _contains_any(research_output.schedule_notes, rest_disadvantage_terms)
    )
    motivation_boost: int = _to_flag(
        _contains_any(research_output.motivation_notes, motivation_boost_terms)
    )
    weather_risk: int = _to_flag(
        _contains_any(research_output.weather_notes, weather_risk_terms)
    )
    info_uncertainty: int = _to_flag(
        bool(research_output.uncertainty_flags) or research_output.source_quality_score < 0.5
    )

    return QuantFeatures(
        event_id=event_id,
        key_player_out=key_player_out,
        lineup_uncertain=lineup_uncertain,
        rest_disadvantage=rest_disadvantage,
        motivation_boost=motivation_boost,
        weather_risk=weather_risk,
        info_uncertainty=info_uncertainty,
        analysis_confidence=analysis_output.confidence_score,
        qualitative_bias=analysis_output.qualitative_bias,
        key_reasons=analysis_output.key_reasons,
        red_flags=analysis_output.red_flags,
    )
