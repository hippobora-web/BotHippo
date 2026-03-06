"""Custom error types for pipeline reliability and failure classification."""


class AgentPipelineError(Exception):
    """Base exception type for agent pipeline errors."""


class ExternalAPIError(AgentPipelineError):
    """Raised when an external API call fails or returns invalid payloads."""


class ConfigurationError(AgentPipelineError):
    """Raised when required runtime configuration is missing or invalid."""


class ParseError(AgentPipelineError):
    """Raised when deterministic parsing fails for expected payload formats."""

