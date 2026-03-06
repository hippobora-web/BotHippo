"""Ticket builder assembling the final pipeline output."""

from evengine.agents.schemas import (
    AnalysisOutput,
    EventInput,
    MarketSnapshot,
    QuantDecision,
    ResearchOutput,
    TicketOutput,
)


def build_ticket(
    *,
    event_input: EventInput,
    market_snapshot: MarketSnapshot,
    research_output: ResearchOutput,
    analysis_output: AnalysisOutput,
    quant_decision: QuantDecision,
) -> TicketOutput:
    """Build the final ticket deterministically from upstream outputs."""

    return TicketOutput(
        event_id=event_input.event_id,
        sport=event_input.sport,
        competition=event_input.competition,
        home_team=event_input.home_team,
        away_team=event_input.away_team,
        market_type=event_input.market_type,
        selection=event_input.selection,
        bookmaker=event_input.bookmaker,
        odds=market_snapshot.odds,
        implied_probability=market_snapshot.implied_probability,
        model_probability=quant_decision.model_probability,
        edge=quant_decision.edge,
        ev=quant_decision.ev,
        decision=quant_decision.decision,
        confidence_score=analysis_output.confidence_score,
        qualitative_bias=analysis_output.qualitative_bias,
        key_reasons=analysis_output.key_reasons,
        red_flags=analysis_output.red_flags,
        uncertainty_flags=research_output.uncertainty_flags,
        recommended_posture=analysis_output.recommended_posture,
        narrative_summary=analysis_output.narrative_summary,
    )

