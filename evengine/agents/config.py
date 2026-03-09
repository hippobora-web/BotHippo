"""Centralized runtime configuration for the agent pipeline."""

from __future__ import annotations

import os


def _safe_int_env(name: str, default: int) -> int:
    """Read an integer environment variable with a safe fallback."""

    raw_value: str | None = os.getenv(name)
    if raw_value is None:
        return default
    try:
        parsed: int = int(raw_value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _safe_bool_env(name: str, default: bool) -> bool:
    """Read a boolean environment variable with a safe fallback."""

    raw_value: str | None = os.getenv(name)
    if raw_value is None:
        return default

    normalized: str = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


PERPLEXITY_API_URL: str = os.getenv(
    "PERPLEXITY_API_URL",
    "https://api.perplexity.ai/chat/completions",
)
PERPLEXITY_MODEL: str = os.getenv("PERPLEXITY_MODEL", "sonar")
OPENAI_API_URL: str = os.getenv(
    "OPENAI_API_URL",
    "https://api.openai.com/v1/chat/completions",
)
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_HTTP_TIMEOUT_SECONDS: int = _safe_int_env("DEFAULT_HTTP_TIMEOUT_SECONDS", 30)
DEFAULT_LOG_DIR: str = os.getenv("DEFAULT_LOG_DIR", "logs")
PIPELINE_HISTORY_FILE: str = os.getenv("PIPELINE_HISTORY_FILE", "pipeline_history.jsonl")
USE_REAL_QUANT_ENGINE: bool = _safe_bool_env("USE_REAL_QUANT_ENGINE", True)
REAL_QUANT_ENGINE_IMPORT_PATH: str = os.getenv("REAL_QUANT_ENGINE_IMPORT_PATH", "")
