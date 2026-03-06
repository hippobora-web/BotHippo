"""Deterministic parser for research agent outputs."""

from __future__ import annotations

import json
import re
from typing import Any

from evengine.agents.schemas import ResearchOutput


_LIST_FIELDS: tuple[str, ...] = (
    "injuries_summary",
    "recent_form_notes",
    "schedule_notes",
    "motivation_notes",
    "weather_notes",
    "uncertainty_flags",
)

_SECTION_KEYWORDS: dict[str, tuple[str, ...]] = {
    "injuries_summary": ("injur", "absence", "suspension"),
    "recent_form_notes": ("recent form", "form", "last", "streak"),
    "schedule_notes": ("schedule", "rest", "travel", "fixture", "calendar"),
    "motivation_notes": ("motivation", "stakes", "context", "title", "playoff", "relegation"),
    "weather_notes": ("weather", "forecast", "rain", "wind", "temperature"),
    "uncertainty_flags": ("uncertainty", "unknown", "unconfirmed", "doubtful"),
}


def _coerce_str_list(value: Any) -> list[str]:
    """Convert a mixed value into a list of non-empty strings."""

    if isinstance(value, str):
        text: str = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            if isinstance(item, str):
                stripped: str = item.strip()
                if stripped:
                    result.append(stripped)
        return result
    return []


def _dedupe(values: list[str]) -> list[str]:
    """Preserve order while removing duplicates."""

    unique: list[str] = []
    seen: set[str] = set()
    for value in values:
        if value not in seen:
            seen.add(value)
            unique.append(value)
    return unique


def _parse_json_text(raw_text: str) -> dict[str, Any] | None:
    """Parse raw text as JSON when possible."""

    try:
        decoded: Any = json.loads(raw_text)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def _field_from_heading(line: str) -> str | None:
    """Map a heading line to a schema field when detected."""

    normalized: str = re.sub(r"^[#\-\*\d\.\)\s]+", "", line).strip().lower()
    heading_key: str = normalized.split(":", 1)[0].strip()
    for field_name, keywords in _SECTION_KEYWORDS.items():
        if any(keyword in heading_key for keyword in keywords):
            return field_name
    return None


def _clean_line_item(line: str) -> str:
    """Normalize bullet or plain text note content."""

    cleaned: str = re.sub(r"^[\-\*\u2022]\s*", "", line).strip()
    return cleaned


def _parse_sectioned_text(raw_text: str) -> dict[str, list[str]]:
    """Parse list-style sectioned text into structured note fields."""

    parsed: dict[str, list[str]] = {name: [] for name in _LIST_FIELDS}
    current_field: str | None = None

    for raw_line in raw_text.splitlines():
        line: str = raw_line.strip()
        if not line:
            continue

        new_field: str | None = _field_from_heading(line)
        if new_field:
            current_field = new_field
            if ":" in line:
                inline_value: str = _clean_line_item(line.split(":", 1)[1])
                if inline_value:
                    parsed[current_field].append(inline_value)
            continue

        if current_field is None:
            continue

        note: str = _clean_line_item(line)
        if note:
            parsed[current_field].append(note)

    for field_name in _LIST_FIELDS:
        parsed[field_name] = _dedupe(parsed[field_name])
    return parsed


def _extract_source_quality_score(payload: dict[str, Any]) -> float:
    """Extract source quality score from JSON payload with a safe default."""

    value: Any = payload.get("source_quality_score", 0.5)
    try:
        numeric_value: float = float(value)
    except (TypeError, ValueError):
        return 0.5
    return max(0.0, min(1.0, numeric_value))


def parse_research_output(
    *,
    event_id: str,
    sport: str,
    competition: str,
    home_team: str,
    away_team: str,
    raw_text: str,
) -> ResearchOutput:
    """Convert raw research text into structured deterministic output."""

    parsed_lists: dict[str, list[str]] = {name: [] for name in _LIST_FIELDS}
    source_quality_score: float = 0.5
    structured: bool = False

    json_payload: dict[str, Any] | None = _parse_json_text(raw_text)
    if json_payload is not None:
        for field_name in _LIST_FIELDS:
            parsed_lists[field_name] = _coerce_str_list(json_payload.get(field_name))
        source_quality_score = _extract_source_quality_score(json_payload)
        structured = any(parsed_lists[field_name] for field_name in _LIST_FIELDS)
    else:
        parsed_lists = _parse_sectioned_text(raw_text)
        structured = any(parsed_lists[field_name] for field_name in _LIST_FIELDS)

    uncertainty_flags: list[str] = parsed_lists["uncertainty_flags"]
    if not structured and "parser_extraction_limited" not in uncertainty_flags:
        uncertainty_flags = [*uncertainty_flags, "parser_extraction_limited"]

    return ResearchOutput(
        event_id=event_id,
        sport=sport,
        competition=competition,
        home_team=home_team,
        away_team=away_team,
        injuries_summary=parsed_lists["injuries_summary"],
        recent_form_notes=parsed_lists["recent_form_notes"],
        schedule_notes=parsed_lists["schedule_notes"],
        motivation_notes=parsed_lists["motivation_notes"],
        weather_notes=parsed_lists["weather_notes"],
        uncertainty_flags=uncertainty_flags,
        source_quality_score=source_quality_score,
        raw_text=raw_text,
    )

