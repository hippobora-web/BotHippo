"""Analysis agent orchestrating prompt, fetch, and parse steps."""

from evengine.agents.analysis_parser import parse_analysis_output
from evengine.agents.errors import ConfigurationError, ExternalAPIError
from evengine.agents.openai_client import fetch_analysis
from evengine.agents.schemas import AnalysisOutput, MarketSnapshot, ResearchOutput


def build_analysis_prompt(
    *,
    event_id: str,
    market_snapshot: MarketSnapshot,
    research_output: ResearchOutput,
) -> str:
    """Build a strict JSON-only prompt for qualitative analysis."""

    return (
        "Analyze the event context and return only a JSON object with exactly these keys:\n"
        "qualitative_bias, key_reasons, red_flags, confidence_score, "
        "recommended_posture, narrative_summary.\n"
        "Rules:\n"
        "- confidence_score must be a float between 0 and 1\n"
        "- key_reasons and red_flags must be arrays of strings\n"
        "- no extra keys, no markdown, no prose outside JSON\n\n"
        f"event_id: {event_id}\n"
        f"market_snapshot: {market_snapshot.model_dump()}\n"
        f"research_output: {research_output.model_dump()}\n\n"
        "Interpret and weigh:\n"
        "- market context\n"
        "- injuries and absences\n"
        "- recent form\n"
        "- schedule/rest context\n"
        "- motivation/stakes\n"
        "- weather relevance\n"
        "- uncertainty flags\n"
    )


def run_analysis(
    *,
    event_id: str,
    market_snapshot: MarketSnapshot,
    research_output: ResearchOutput,
) -> AnalysisOutput:
    """Run analysis flow and return structured qualitative output."""

    prompt: str = build_analysis_prompt(
        event_id=event_id,
        market_snapshot=market_snapshot,
        research_output=research_output,
    )

    try:
        raw_text: str = fetch_analysis(prompt)
    except ConfigurationError:
        return _build_analysis_fallback(
            event_id=event_id,
            failure_flag="analysis_configuration_error",
        )
    except ExternalAPIError:
        return _build_analysis_fallback(
            event_id=event_id,
            failure_flag="analysis_external_api_error",
        )
    except Exception:
        return _build_analysis_fallback(
            event_id=event_id,
            failure_flag="analysis_unknown_error",
        )

    return parse_analysis_output(event_id=event_id, raw_text=raw_text)


def _build_analysis_fallback(*, event_id: str, failure_flag: str) -> AnalysisOutput:
    """Build a deterministic fallback when analysis fetch fails."""

    return AnalysisOutput(
        event_id=event_id,
        qualitative_bias="neutral",
        key_reasons=[],
        red_flags=["analysis_fetch_failed", failure_flag],
        confidence_score=0.0,
        recommended_posture="watch",
        narrative_summary="",
        raw_text="",
    )
