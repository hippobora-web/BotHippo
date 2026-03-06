"""Queue helpers for sequential local development orchestration."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dev_orchestrator.schemas import (
    DevTaskRequest,
    PersistentQueueState,
    PersistentQueueTaskState,
    QueueRunSummary,
    QueuedTaskItem,
)


def _timestamp() -> str:
    """Return a deterministic UTC timestamp string."""

    return datetime.now(timezone.utc).isoformat()


def _normalize_queue_payload(payload: Any) -> list[Any]:
    """Normalize top-level queue payload into a raw list of task items."""

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("tasks"), list):
        return payload["tasks"]
    raise ValueError("invalid_queue_structure")


def _normalized_item_payload(raw_item: Any) -> dict[str, Any]:
    """Normalize one raw queue item into a safe dict for model validation."""

    if not isinstance(raw_item, dict):
        return {"task": "", "test_commands": []}

    raw_test_commands: Any = raw_item.get("test_commands", [])
    test_commands: list[str] = []
    if isinstance(raw_test_commands, list):
        test_commands = [item for item in raw_test_commands if isinstance(item, str)]

    return {
        "task": raw_item.get("task") if isinstance(raw_item.get("task"), str) else "",
        "run_codex": raw_item.get("run_codex") if isinstance(raw_item.get("run_codex"), int) else None,
        "run_tests": raw_item.get("run_tests") if isinstance(raw_item.get("run_tests"), int) else None,
        "codex_command": raw_item.get("codex_command")
        if isinstance(raw_item.get("codex_command"), str)
        else None,
        "codex_timeout_seconds": raw_item.get("codex_timeout_seconds")
        if isinstance(raw_item.get("codex_timeout_seconds"), int)
        else None,
        "codex_prompt_via_stdin": raw_item.get("codex_prompt_via_stdin")
        if isinstance(raw_item.get("codex_prompt_via_stdin"), int)
        else None,
        "test_commands": test_commands,
    }


def load_task_queue(queue_path: str) -> list[QueuedTaskItem]:
    """Load a local JSON task queue into validated queued task items."""

    try:
        raw_text: str = Path(queue_path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError("queue_file_not_found") from exc
    except OSError as exc:
        raise ValueError("queue_file_unreadable") from exc

    try:
        payload: Any = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_queue_json") from exc

    raw_items: list[Any] = _normalize_queue_payload(payload)
    return [
        QueuedTaskItem.model_validate(_normalized_item_payload(raw_item))
        for raw_item in raw_items
    ]


def default_state_path(queue_path: str) -> str:
    """Return the default persistent state file path for a queue file."""

    return str(Path(queue_path).with_suffix(".state.json"))


def initialize_queue_state(
    *,
    queue_path: str,
    state_path: str,
    queued_items: list[QueuedTaskItem],
) -> PersistentQueueState:
    """Initialize a fresh persistent queue state."""

    now: str = _timestamp()
    tasks: list[PersistentQueueTaskState] = [
        PersistentQueueTaskState(
            task=item.task,
            status="pending",
            queue_index=index,
            result={},
        )
        for index, item in enumerate(queued_items, start=1)
    ]
    return PersistentQueueState(
        queue_path=queue_path,
        state_path=state_path,
        started_at=now,
        updated_at=now,
        finished_at="",
        tasks=tasks,
    )


def is_terminal_status(status: str) -> bool:
    """Return 1-like truth when a queue task status is terminal."""

    return status in {"done", "failed", "skipped"}


def save_queue_state(state: PersistentQueueState) -> None:
    """Persist queue state as human-readable UTF-8 JSON."""

    updated_at: str = _timestamp()
    finished_at: str = (
        updated_at
        if state.tasks and all(is_terminal_status(task.status) for task in state.tasks)
        else ""
    )
    updated_state: PersistentQueueState = state.model_copy(
        update={
            "updated_at": updated_at,
            "finished_at": finished_at,
        }
    )

    state_file: Path = Path(updated_state.state_path)
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(updated_state.model_dump_json(indent=2), encoding="utf-8")


def _load_persistent_state(state_path: str) -> PersistentQueueState:
    """Load a persistent queue state file with safe validation errors."""

    try:
        raw_text: str = Path(state_path).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValueError("queue_state_not_found") from exc
    except OSError as exc:
        raise ValueError("queue_state_unreadable") from exc

    try:
        payload: Any = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_queue_state_json") from exc

    try:
        return PersistentQueueState.model_validate(payload)
    except Exception as exc:
        raise ValueError("invalid_queue_state") from exc


def load_or_initialize_queue_state(
    *,
    queue_path: str,
    state_path: str,
    queued_items: list[QueuedTaskItem],
    resume: int,
) -> PersistentQueueState:
    """Load an existing queue state or initialize a fresh one."""

    if resume == 1 and Path(state_path).exists():
        state: PersistentQueueState = _load_persistent_state(state_path)
        if len(state.tasks) != len(queued_items):
            raise ValueError("queue_state_mismatch")
        for index, item in enumerate(queued_items, start=1):
            persisted_task: PersistentQueueTaskState = state.tasks[index - 1]
            if persisted_task.queue_index != index or persisted_task.task != item.task:
                raise ValueError("queue_state_mismatch")
        return state

    state = initialize_queue_state(
        queue_path=queue_path,
        state_path=state_path,
        queued_items=queued_items,
    )
    save_queue_state(state)
    return _load_persistent_state(state_path)


def update_task_state(
    *,
    state: PersistentQueueState,
    queue_index: int,
    status: str,
    result: dict | None = None,
) -> PersistentQueueState:
    """Return an updated persistent queue state for one task."""

    updated_tasks: list[PersistentQueueTaskState] = []
    for task_state in state.tasks:
        if task_state.queue_index == queue_index:
            updated_tasks.append(
                task_state.model_copy(
                    update={
                        "status": status,
                        "result": task_state.result if result is None else result,
                    }
                )
            )
        else:
            updated_tasks.append(task_state)

    return state.model_copy(update={"tasks": updated_tasks})


def build_request_from_queue_item(
    *,
    item: QueuedTaskItem,
    default_workdir: str,
    default_run_codex: int,
    default_run_tests: int,
    default_codex_command: str | None,
    default_codex_timeout_seconds: int,
    default_codex_prompt_via_stdin: int,
) -> DevTaskRequest:
    """Build a single-task request from one queued task item and defaults."""

    task: str = item.task.strip()
    if not task:
        raise ValueError("invalid_queue_task")

    return DevTaskRequest(
        task=task,
        workdir=default_workdir,
        run_codex=default_run_codex if item.run_codex is None else item.run_codex,
        run_tests=default_run_tests if item.run_tests is None else item.run_tests,
        codex_command=default_codex_command if item.codex_command is None else item.codex_command,
        codex_timeout_seconds=(
            default_codex_timeout_seconds
            if item.codex_timeout_seconds is None
            else item.codex_timeout_seconds
        ),
        codex_prompt_via_stdin=(
            default_codex_prompt_via_stdin
            if item.codex_prompt_via_stdin is None
            else item.codex_prompt_via_stdin
        ),
        test_commands=item.test_commands,
    )


def summarize_queue_results(results: list[dict]) -> QueueRunSummary:
    """Summarize queue results using success and merge recommendation fields."""

    total_tasks: int = len(results)
    succeeded: int = sum(1 for result in results if result.get("success") == 1)
    failed: int = sum(1 for result in results if result.get("merge_recommendation") == "failed")
    needs_review: int = sum(
        1 for result in results if result.get("merge_recommendation") == "needs_review"
    )
    failed_after_repair: int = sum(
        1
        for result in results
        if result.get("merge_recommendation") == "failed_after_repair"
    )
    ready_for_pr: int = sum(
        1 for result in results if result.get("merge_recommendation") == "ready_for_pr"
    )

    return QueueRunSummary(
        total_tasks=total_tasks,
        succeeded=succeeded,
        failed=failed,
        needs_review=needs_review,
        failed_after_repair=failed_after_repair,
        ready_for_pr=ready_for_pr,
    )
