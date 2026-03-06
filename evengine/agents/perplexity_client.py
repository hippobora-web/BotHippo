"""Minimal Perplexity API client wrapper."""

from __future__ import annotations

import os
from typing import Any

import requests


PERPLEXITY_API_URL: str = "https://api.perplexity.ai/chat/completions"
PERPLEXITY_MODEL: str = "sonar"


def _get_api_key() -> str:
    """Return Perplexity API key from environment."""

    api_key: str | None = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY environment variable is required")
    return api_key


def fetch_event_research(prompt: str) -> str:
    """Fetch raw research text for an event from Perplexity."""

    api_key: str = _get_api_key()
    headers: dict[str, str] = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {
        "model": PERPLEXITY_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise sports research assistant."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }

    response: requests.Response = requests.post(
        PERPLEXITY_API_URL,
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    data: dict[str, Any] = response.json()

    try:
        content: Any = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Unexpected response format from Perplexity API") from exc

    if not isinstance(content, str):
        raise ValueError("Perplexity response content is not text")

    return content.strip()

