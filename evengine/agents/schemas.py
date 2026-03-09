"""Shared Pydantic schemas for the agent pipeline."""

from __future__ import annotations

from typing import Optional

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


class UniverseCandidate(BaseModel):
    """Candidate market/event with a deterministic priority score."""

    event_id: str
    sport: str
    competition: str
    home_team: str
    away_team: str
    market_type: str
    selection: str
    bookmaker: str
    odds: float
    timestamp: str
    priority_score: float
    candidate_flags: list[str] = Field(default_factory=list)


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


class QuantAgentMetadata(BaseModel):
    """Metadata describing which quant engine mode produced the decision."""

    engine_mode: str
    used_real_engine: int
    fallback_reason: str
    baseline_quality: str = ""
    coverage_level: str = ""
    extra_flags: list[str] = Field(default_factory=list)


class QuantDecision(BaseModel):
    """Quant engine decision payload for downstream ticketing."""

    event_id: str
    decision: str
    model_probability: float
    implied_probability: float
    edge: float
    ev: float
    metadata: Optional[QuantAgentMetadata] = None


class RiskDecision(BaseModel):
    """Risk layer decision describing allowance and recommended stake."""

    event_id: str
    allowed: int
    recommended_stake_eur: float
    bankroll_fraction: float
    risk_flags: list[str] = Field(default_factory=list)
    risk_reason: str
    kill_switch: int


class AnalysisOutput(BaseModel):
    """Structured qualitative analysis output for one event."""

    event_id: str
    qualitative_bias: str
    key_reasons: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    confidence_score: float
    recommended_posture: str
    narrative_summary: str
    raw_text: str


class QuantFeatures(BaseModel):
    """Structured quant-ready features mapped from research and analysis outputs."""

    event_id: str
    key_player_out: int
    lineup_uncertain: int
    rest_disadvantage: int
    motivation_boost: int
    weather_risk: int
    info_uncertainty: int
    analysis_confidence: float
    qualitative_bias: str
    key_reasons: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)


class TicketOutput(BaseModel):
    """Final ticket payload assembled from all pipeline stages."""

    event_id: str
    sport: str
    competition: str
    home_team: str
    away_team: str
    market_type: str
    selection: str
    bookmaker: str
    odds: float
    implied_probability: float
    model_probability: float
    edge: float
    ev: float
    decision: str
    confidence_score: float
    qualitative_bias: str
    key_reasons: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    uncertainty_flags: list[str] = Field(default_factory=list)
    recommended_posture: str
    narrative_summary: str
    risk_allowed: Optional[int] = None
    recommended_stake_eur: Optional[float] = None
    bankroll_fraction: Optional[float] = None
    risk_flags: list[str] = Field(default_factory=list)
    risk_reason: str = ""
    kill_switch: Optional[int] = None


class PipelineRunRecord(BaseModel):
    """Serializable full pipeline record for audit/history persistence."""

    event_id: str
    timestamp: str
    event_input: dict
    market_snapshot: dict
    research_output: dict
    analysis_output: dict
    quant_features: dict
    quant_decision: dict
    ticket_output: dict
