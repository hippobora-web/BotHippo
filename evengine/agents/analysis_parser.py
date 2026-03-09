"""Deterministic parser for analysis agent outputs."""

from __future__ import annotations

import json
from typing import Any

from evengine.agents.schemas import AnalysisOutput


def _coerce_str(value: Any, default: str = "") -> str:
    """Convert a value to a stripped string with a safe default."""

    if isinstance(value, str):
        stripped: str = value.strip()
        return stripped if stripped else default
    return default


def _coerce_str_list(value: Any) -> list[str]:
    """Convert a mixed value to a list of non-empty strings."""

    if isinstance(value, str):
        stripped: str = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        items: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped: str = item.strip()
                if stripped:
                    items.append(stripped)
        return items
    return []


def _clamp_score(value: Any, default: float = 0.5) -> float:
    """Clamp a numeric confidence score between 0 and 1."""

    try:
        numeric: float = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, min(1.0, numeric))


def parse_analysis_output(
    *,
    event_id: str,
    raw_text: str,
) -> AnalysisOutput:
    """Parse raw analysis text into a strict AnalysisOutput model."""

    defaults: dict[str, Any] = {
        "qualitative_bias": "neutral",
        "key_reasons": [],
        "red_flags": ["analysis_parse_limited"],
        "confidence_score": 0.5,
        "recommended_posture": "watch",
        "narrative_summary": "",
    }

    try:
        payload: Any = json.loads(raw_text)
    except json.JSONDecodeError:
        payload = None

    if not isinstance(payload, dict):
        return AnalysisOutput(
            event_id=event_id,
            qualitative_bias=defaults["qualitative_bias"],
            key_reasons=defaults["key_reasons"],
            red_flags=defaults["red_flags"],
            confidence_score=defaults["confidence_score"],
            recommended_posture=defaults["recommended_posture"],
            narrative_summary=defaults["narrative_summary"],
            raw_text=raw_text,
        )

    qualitative_bias: str = _coerce_str(payload.get("qualitative_bias"), defaults["qualitative_bias"])
    key_reasons: list[str] = _coerce_str_list(payload.get("key_reasons"))
    red_flags: list[str] = _coerce_str_list(payload.get("red_flags"))
    confidence_score: float = _clamp_score(payload.get("confidence_score"), defaults["confidence_score"])
    recommended_posture: str = _coerce_str(payload.get("recommended_posture"), defaults["recommended_posture"])
    narrative_summary: str = _coerce_str(payload.get("narrative_summary"), defaults["narrative_summary"])

    missing_or_limited: bool = any(
        [
            "qualitative_bias" not in payload,
            "key_reasons" not in payload,
            "red_flags" not in payload,
            "confidence_score" not in payload,
            "recommended_posture" not in payload,
            "narrative_summary" not in payload,
        ]
    )
    if not red_flags:
        red_flags = defaults["red_flags"] if missing_or_limited else []
    elif missing_or_limited and "analysis_parse_limited" not in red_flags:
        red_flags = [*red_flags, "analysis_parse_limited"]

    return AnalysisOutput(
        event_id=event_id,
        qualitative_bias=qualitative_bias,
        key_reasons=key_reasons,
        red_flags=red_flags,
        confidence_score=confidence_score,
        recommended_posture=recommended_posture,
        narrative_summary=narrative_summary,
        raw_text=raw_text,
    )

