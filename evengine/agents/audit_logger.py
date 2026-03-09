"""Local JSONL audit logging helpers for pipeline history."""

from __future__ import annotations

import json
from pathlib import Path

from evengine.agents.config import DEFAULT_LOG_DIR, PIPELINE_HISTORY_FILE
from evengine.agents.schemas import PipelineRunRecord


def ensure_log_dir(path: str) -> None:
    """Ensure a log directory exists."""

    Path(path).mkdir(parents=True, exist_ok=True)


def append_jsonl(path: str, payload: dict) -> None:
    """Append one JSON object as a JSONL line."""

    with Path(path).open("a", encoding="utf-8") as file:
        file.write(json.dumps(payload, ensure_ascii=False) + "\n")


def log_pipeline_run(record: PipelineRunRecord, log_dir: str = DEFAULT_LOG_DIR) -> str:
    """Persist a pipeline run record and return the history file path."""

    ensure_log_dir(log_dir)
    history_path: Path = Path(log_dir) / PIPELINE_HISTORY_FILE
    append_jsonl(str(history_path), record.model_dump())
    return str(history_path)
