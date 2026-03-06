"""Supervisor orchestrator for the multi-agent pipeline."""

from datetime import datetime, timezone

from evengine.agents.analysis_agent import run_analysis
from evengine.agents.audit_logger import log_pipeline_run
from evengine.agents.feature_mapper import map_to_quant_features
from evengine.agents.market_agent import process_market
from evengine.agents.quant_agent import run_quant
from evengine.agents.risk_agent import run_risk
from evengine.agents.research_agent import run_research
from evengine.agents.schemas import EventInput, PipelineRunRecord, TicketOutput
from evengine.agents.ticket_builder import build_ticket


def run_pipeline(event: EventInput) -> TicketOutput:
    """Run the full pipeline and return the final ticket output."""

    print("Supervisor: starting pipeline")
    print("Supervisor: running market agent")
    snapshot = process_market(event)
    print("Market agent completed")
    print(snapshot.model_dump())

    print("Supervisor: running research agent")
    research_output = run_research(event)
    print("Research agent completed")
    print(research_output.model_dump())

    print("Supervisor: running analysis agent")
    analysis_output = run_analysis(
        event_id=event.event_id,
        market_snapshot=snapshot,
        research_output=research_output,
    )
    print("Analysis agent completed")
    print(analysis_output.model_dump())

    print("Supervisor: running feature mapper")
    quant_features = map_to_quant_features(
        event_id=event.event_id,
        research_output=research_output,
        analysis_output=analysis_output,
    )
    print("Feature mapper completed")
    print(quant_features.model_dump())

    print("Supervisor: running quant agent")
    quant_decision = run_quant(
        event_id=event.event_id,
        market_snapshot=snapshot,
        quant_features=quant_features,
    )
    print("Quant agent completed")
    print(quant_decision.model_dump())

    print("Supervisor: running risk agent")
    risk_decision = run_risk(
        event_input=event,
        quant_decision=quant_decision,
    )
    print("Risk agent completed")
    print(risk_decision.model_dump())

    print("Supervisor: running ticket builder")
    ticket_output: TicketOutput = build_ticket(
        event_input=event,
        market_snapshot=snapshot,
        research_output=research_output,
        analysis_output=analysis_output,
        quant_decision=quant_decision,
    )
    ticket_output = ticket_output.model_copy(
        update={
            "risk_allowed": risk_decision.allowed,
            "recommended_stake_eur": risk_decision.recommended_stake_eur,
            "bankroll_fraction": risk_decision.bankroll_fraction,
            "risk_flags": risk_decision.risk_flags,
            "risk_reason": risk_decision.risk_reason,
            "kill_switch": risk_decision.kill_switch,
        }
    )
    print("Ticket builder completed")
    print(ticket_output.model_dump())

    record = PipelineRunRecord(
        event_id=event.event_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        event_input=event.model_dump(),
        market_snapshot=snapshot.model_dump(),
        research_output=research_output.model_dump(),
        analysis_output=analysis_output.model_dump(),
        quant_features=quant_features.model_dump(),
        quant_decision=quant_decision.model_dump(),
        ticket_output=ticket_output.model_dump(),
    )
    print("Supervisor: writing audit log")
    history_path: str = log_pipeline_run(record)
    print("Audit log completed")
    print(history_path)

    return ticket_output
