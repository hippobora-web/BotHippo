"""Shared Pydantic schemas for the agent pipeline."""

from pydantic import BaseModel, Field


class EventInput(BaseModel):
    """Raw event and market input consumed by the supervisor."""

    event_id: str
    sport: str
    competition: str
    home_team: str
    away_team: str
    market_type: str
    selection: str
    odds: float
    bookmaker: str
    timestamp: str


class MarketSnapshot(BaseModel):
    """Normalized market view produced by the market agent."""

    event_id: str
    market_type: str
    selection: str
    odds: float
    implied_probability: float
    bookmaker: str
    timestamp: str


class ResearchOutput(BaseModel):
    """Structured contextual research output for an event."""

    event_id: str
    sport: str
    competition: str
    home_team: str
    away_team: str
    injuries_summary: list[str] = Field(default_factory=list)
    recent_form_notes: list[str] = Field(default_factory=list)
    schedule_notes: list[str] = Field(default_factory=list)
    motivation_notes: list[str] = Field(default_factory=list)
    weather_notes: list[str] = Field(default_factory=list)
    uncertainty_flags: list[str] = Field(default_factory=list)
    source_quality_score: float = 0.5
    raw_text: str


class QuantDecision(BaseModel):
    """Quant engine decision payload for downstream ticketing."""

    event_id: str
    decision: str
    model_probability: float
    implied_probability: float
    edge: float
    ev: float
