"""Bounded autonomous loop helpers for the local development orchestrator."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from dev_orchestrator.git_runner import is_repo_clean
from dev_orchestrator.schemas import AutoLoopCycleResult, AutoLoopResult, DiscoveryResult, DiscoveredTask
from dev_orchestrator.task_discovery import discover_tasks, write_discovery_queue


_ALLOWED_AUTO_TASK_PREFIXES: tuple[str, ...] = (
    "add tests for ",
    "resolve TODOs in ",
)


def _timestamp() -> str:
    """Return a deterministic UTC timestamp string."""

    return datetime.now(timezone.utc).isoformat()


def _is_allowed_auto_task(task: DiscoveredTask) -> bool:
    """Return True when a discovered task is safe for autonomous execution."""

    return task.task.startswith(_ALLOWED_AUTO_TASK_PREFIXES)


def _filter_auto_tasks(tasks: list[DiscoveredTask]) -> list[DiscoveredTask]:
    """Filter discovered tasks down to the conservative autonomous subset."""

    return [task for task in tasks if _is_allowed_auto_task(task)]


def _queue_path_for_cycle(queue_dir: str, cycle_index: int) -> str:
    """Build deterministic queue file path for one cycle."""

    return str(Path(queue_dir) / f"auto_cycle_{cycle_index:03d}.json")


def _effective_queue_dir(workdir: str, queue_dir: str) -> str:
    """Resolve a queue directory without polluting the target repository by default."""

    queue_dir_path: Path = Path(queue_dir)
    if queue_dir_path.is_absolute():
        return str(queue_dir_path)
    return str(Path(workdir).resolve().parent / queue_dir_path)


def _cycle_made_progress(queue_result: dict) -> bool:
    """Return True when a queue result indicates useful forward progress."""

    summary: dict = queue_result.get("summary", {})
    return summary.get("succeeded", 0) > 0 or summary.get("ready_for_pr", 0) > 0


def run_autonomous_loop(
    *,
    workdir: str,
    max_cycles: int,
    max_tasks_per_cycle: int,
    queue_dir: str,
    run_codex: int,
    run_tests: int,
    codex_command: str | None,
    codex_timeout_seconds: int,
    codex_prompt_via_stdin: int,
) -> AutoLoopResult:
    """Run a bounded discovery -> queue -> execute loop with conservative stop rules."""

    from dev_orchestrator.supervisor import run_development_queue

    started_at: str = _timestamp()
    if is_repo_clean(workdir) != 1:
        return AutoLoopResult(
            workdir=workdir,
            started_at=started_at,
            finished_at=_timestamp(),
            max_cycles=max_cycles,
            completed_cycles=0,
            cycles=[],
            stopped_reason="dirty_repo_at_start",
        )

    completed_cycles: int = 0
    cycle_results: list[AutoLoopCycleResult] = []
    stopped_reason: str = "max_cycles_reached"
    effective_queue_dir: str = _effective_queue_dir(workdir, queue_dir)

    for cycle_index in range(1, max_cycles + 1):
        discovery_result: DiscoveryResult = discover_tasks(workdir)
        filtered_tasks: list[DiscoveredTask] = _filter_auto_tasks(discovery_result.tasks)
        if not filtered_tasks:
            stopped_reason = "no_tasks_discovered"
            break

        capped_tasks: list[DiscoveredTask] = filtered_tasks[: max(0, max_tasks_per_cycle)]
        if not capped_tasks:
            stopped_reason = "no_tasks_discovered"
            break

        cycle_queue_path: str = _queue_path_for_cycle(effective_queue_dir, cycle_index)
        bounded_discovery_result: DiscoveryResult = discovery_result.model_copy(
            update={
                "tasks": capped_tasks,
                "output_queue_path": cycle_queue_path,
            }
        )
        written_queue_path: str = write_discovery_queue(
            discovery_result=bounded_discovery_result,
            queue_path=cycle_queue_path,
        )
        queue_result = run_development_queue(
            queue_path=written_queue_path,
            default_workdir=workdir,
            default_run_codex=run_codex,
            default_run_tests=run_tests,
            default_codex_command=codex_command,
            default_codex_timeout_seconds=codex_timeout_seconds,
            default_codex_prompt_via_stdin=codex_prompt_via_stdin,
            resume=0,
            state_path=None,
        )
        cycle_result: AutoLoopCycleResult = AutoLoopCycleResult(
            cycle_index=cycle_index,
            discovered_task_count=len(filtered_tasks),
            queue_path=written_queue_path,
            queue_result=queue_result.model_dump(),
            stopped_reason="",
        )
        cycle_results.append(cycle_result)
        completed_cycles = cycle_index

        if is_repo_clean(workdir) != 1:
            cycle_results[-1] = cycle_result.model_copy(update={"stopped_reason": "dirty_repo_after_queue"})
            stopped_reason = "dirty_repo_after_queue"
            break

        if not _cycle_made_progress(queue_result.model_dump()):
            cycle_results[-1] = cycle_result.model_copy(update={"stopped_reason": "no_progress"})
            stopped_reason = "no_progress"
            break

    return AutoLoopResult(
        workdir=workdir,
        started_at=started_at,
        finished_at=_timestamp(),
        max_cycles=max_cycles,
        completed_cycles=completed_cycles,
        cycles=cycle_results,
        stopped_reason=stopped_reason,
    )
