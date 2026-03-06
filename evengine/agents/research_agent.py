"""Research agent orchestrating prompt, fetch, and parse steps."""

from evengine.agents.perplexity_client import fetch_event_research
from evengine.agents.research_parser import parse_research_output
from evengine.agents.schemas import EventInput, ResearchOutput


def build_research_prompt(
    *,
    event_id: str,
    sport: str,
    competition: str,
    home_team: str,
    away_team: str,
) -> str:
    """Build a strict prompt requesting structured sports research."""

    return (
        "Gather concise pre-match research for the event below.\n"
        "Return only a JSON object with exactly these keys:\n"
        "injuries_summary, recent_form_notes, schedule_notes, motivation_notes, "
        "weather_notes, uncertainty_flags, source_quality_score.\n"
        "Use arrays of strings for note fields, and a float 0-1 for source_quality_score.\n"
        "If information is unavailable, return an empty array for that field and add an "
        "uncertainty flag.\n\n"
        f"event_id: {event_id}\n"
        f"sport: {sport}\n"
        f"competition: {competition}\n"
        f"home_team: {home_team}\n"
        f"away_team: {away_team}\n"
        "Research scope:\n"
        "- injuries and absences\n"
        "- recent form\n"
        "- schedule/rest context\n"
        "- motivation/stakes\n"
        "- weather if relevant\n"
        "- uncertainties and confidence limits\n"
    )


def run_research(event: EventInput) -> ResearchOutput:
    """Run research flow for one event and return structured output, resilient by design."""

    prompt: str = build_research_prompt(
        event_id=event.event_id,
        sport=event.sport,
        competition=event.competition,
        home_team=event.home_team,
        away_team=event.away_team,
    )

    try:
        raw_text: str = fetch_event_research(prompt)
    except Exception:
        return ResearchOutput(
            event_id=event.event_id,
            sport=event.sport,
            competition=event.competition,
            home_team=event.home_team,
            away_team=event.away_team,
            injuries_summary=[],
            recent_form_notes=[],
            schedule_notes=[],
            motivation_notes=[],
            weather_notes=[],
            uncertainty_flags=["research_fetch_failed"],
            source_quality_score=0.0,
            raw_text="",
        )

    return parse_research_output(
        event_id=event.event_id,
        sport=event.sport,
        competition=event.competition,
        home_team=event.home_team,
        away_team=event.away_team,
        raw_text=raw_text,
    )
