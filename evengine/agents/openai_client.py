"""Minimal OpenAI API client wrapper for qualitative analysis."""

from __future__ import annotations

import os
from typing import Any

import requests

from evengine.agents.config import (
    DEFAULT_HTTP_TIMEOUT_SECONDS,
    OPENAI_API_URL,
    OPENAI_MODEL,
)
from evengine.agents.errors import ConfigurationError, ExternalAPIError


def _get_api_key() -> str:
    """Return OpenAI API key from environment."""

    api_key: str | None = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ConfigurationError("OPENAI_API_KEY environment variable is required")
    return api_key


def fetch_analysis(prompt: str) -> str:
    """Fetch raw analysis text from OpenAI chat completions."""

    api_key: str = _get_api_key()
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": OPENAI_MODEL,
        "messages": [
            {"role": "system", "content": "You are a rigorous sports betting analyst."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }

    try:
        response: requests.Response = requests.post(
            OPENAI_API_URL,
            headers=headers,
            json=payload,
            timeout=DEFAULT_HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()
    except requests.RequestException as exc:
        raise ExternalAPIError("OpenAI API request failed") from exc
    except ValueError as exc:
        raise ExternalAPIError("OpenAI API returned invalid JSON") from exc

    try:
        content: Any = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ExternalAPIError("Unexpected response format from OpenAI API") from exc

    if not isinstance(content, str):
        raise ExternalAPIError("OpenAI response content is not text")

    return content.strip()
