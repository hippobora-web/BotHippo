"""Deterministic repository task discovery helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from dev_orchestrator.schemas import DiscoveryResult, DiscoveredTask


_IGNORED_DIRS: set[str] = {".git", "__pycache__", "logs", "node_modules", ".venv", "venv"}
_MAX_DISCOVERED_TASKS: int = 20
_LARGE_FILE_THRESHOLD: int = 400


def _timestamp() -> str:
    """Return a deterministic UTC timestamp string."""

    return datetime.now(timezone.utc).isoformat()


def _relative_path(repo_path: str, path: Path) -> str:
    """Return repository-relative POSIX path."""

    return path.relative_to(Path(repo_path)).as_posix()


def _is_ignored_path(path: Path) -> bool:
    """Return 1-like truth when a path should be ignored during discovery."""

    return any(part in _IGNORED_DIRS for part in path.parts)


def collect_python_files(repo_path: str) -> list[str]:
    """Recursively collect Python files while ignoring cache and environment paths."""

    repo_root: Path = Path(repo_path)
    python_files: list[str] = []
    for path in repo_root.rglob("*.py"):
        if _is_ignored_path(path):
            continue
        python_files.append(path.relative_to(repo_root).as_posix())
    return sorted(python_files)


def scan_text_file_for_markers(path: str, markers: tuple[str, ...]) -> list[str]:
    """Scan a text file for markers and return up to a few safe evidence snippets."""

    file_path: Path = Path(path)
    try:
        lines: list[str] = file_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []

    matches: list[str] = []
    for line_number, line in enumerate(lines, start=1):
        if any(marker in line for marker in markers):
            snippet: str = " ".join(line.strip().split())
            matches.append(f"{file_path.name}:{line_number}: {snippet[:120]}")
        if len(matches) >= 3:
            break
    return matches


def _line_count(path: Path) -> int:
    """Return text line count or zero for unreadable files."""

    try:
        return len(path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeDecodeError):
        return 0


def _test_files(repo_path: str) -> list[str]:
    """Collect repository-relative Python test files."""

    python_files: list[str] = collect_python_files(repo_path)
    return [
        path
        for path in python_files
        if "/tests/" in f"/{path}" or Path(path).name.startswith("test_") or Path(path).stem.endswith("_test")
    ]


def _has_related_test(module_path: str, test_files: list[str]) -> bool:
    """Return 1-like truth when a likely related test file exists for a module."""

    stem: str = Path(module_path).stem
    candidates: tuple[str, ...] = (
        f"test_{stem}.py",
        f"{stem}_test.py",
        stem,
    )
    return any(any(candidate in test_file for candidate in candidates) for test_file in test_files)


def _important_module_paths(repo_path: str) -> list[str]:
    """Return a bounded list of important module paths for missing-test heuristics."""

    candidates: list[str] = [
        "dev_orchestrator/supervisor.py",
        "dev_orchestrator/queue_runner.py",
        "evengine/agents/supervisor.py",
        "evengine/agents/quant_agent.py",
    ]
    repo_root: Path = Path(repo_path)
    return [path for path in candidates if (repo_root / path).exists()]


def _add_task(
    discovered: dict[tuple[str, str], DiscoveredTask],
    *,
    task: str,
    priority: int,
    source: str,
    evidence: list[str],
) -> None:
    """Add one deduplicated discovered task."""

    key: tuple[str, str] = (task, source)
    if key in discovered:
        return
    discovered[key] = DiscoveredTask(
        task=task,
        priority=priority,
        source=source,
        evidence=evidence[:3],
    )


def discover_tasks(repo_path: str) -> DiscoveryResult:
    """Inspect the repository deterministically and generate candidate tasks."""

    started_at: str = _timestamp()
    repo_root: Path = Path(repo_path)
    python_files: list[str] = collect_python_files(repo_path)
    discovered: dict[tuple[str, str], DiscoveredTask] = {}

    for relative_path in python_files:
        absolute_path: Path = repo_root / relative_path
        if relative_path == "dev_orchestrator/task_discovery.py":
            continue

        todo_matches: list[str] = scan_text_file_for_markers(str(absolute_path), ("TODO", "FIXME"))
        if todo_matches:
            _add_task(
                discovered,
                task=f"resolve TODOs in {relative_path}",
                priority=80,
                source="todo_scan",
                evidence=[relative_path, *todo_matches],
            )

        if relative_path.startswith(("dev_orchestrator/", "evengine/")):
            line_count: int = _line_count(absolute_path)
            if line_count > _LARGE_FILE_THRESHOLD:
                _add_task(
                    discovered,
                    task=f"refactor oversized module {relative_path}",
                    priority=50,
                    source="large_file_scan",
                    evidence=[relative_path, f"lines={line_count}"],
                )

        pass_matches: list[str] = [
            match
            for match in scan_text_file_for_markers(str(absolute_path), ("pass",))
            if ": pass" in match or match.endswith(": pass")
        ]
        if pass_matches and relative_path not in {"dev_orchestrator/task_discovery.py"}:
            _add_task(
                discovered,
                task=f"replace placeholder pass statements in {relative_path}",
                priority=60,
                source="placeholder_scan",
                evidence=[relative_path, *pass_matches],
            )

    test_files: list[str] = _test_files(repo_path)
    for module_path in _important_module_paths(repo_path):
        if not _has_related_test(module_path, test_files):
            _add_task(
                discovered,
                task=f"add tests for {module_path}",
                priority=70,
                source="missing_test_scan",
                evidence=[module_path, f"known_tests={len(test_files)}"],
            )

    tasks: list[DiscoveredTask] = sorted(
        discovered.values(),
        key=lambda item: (-item.priority, item.task, item.source),
    )[:_MAX_DISCOVERED_TASKS]
    finished_at: str = _timestamp()
    return DiscoveryResult(
        repo_path=repo_path,
        started_at=started_at,
        finished_at=finished_at,
        tasks=tasks,
        output_queue_path="",
    )


def write_discovery_queue(
    *,
    discovery_result: DiscoveryResult,
    queue_path: str,
) -> str:
    """Write a discovered task queue using the existing queue format."""

    sorted_tasks: list[DiscoveredTask] = sorted(
        discovery_result.tasks,
        key=lambda item: (-item.priority, item.task, item.source),
    )
    payload: dict[str, list[dict[str, str]]] = {
        "tasks": [{"task": task.task} for task in sorted_tasks]
    }
    output_path: Path = Path(queue_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(output_path)
