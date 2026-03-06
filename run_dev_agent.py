"""CLI entrypoint for the local development orchestrator."""

from __future__ import annotations

import argparse
import sys

from dev_orchestrator.schemas import AutoLoopResult, DevTaskRequest, DiscoveryResult, QueueRunResult
from dev_orchestrator.supervisor import (
    run_autonomous_development_loop,
    run_development_queue,
    run_development_task,
    run_task_discovery,
)


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the development orchestrator."""

    parser = argparse.ArgumentParser(description="Run local dev orchestrator workflow.")
    parser.add_argument("task", nargs="*", help="Development task description.")
    parser.add_argument(
        "--queue",
        default=None,
        help="Path to a JSON queue file containing multiple tasks.",
    )
    parser.add_argument(
        "--auto-loop",
        action="store_true",
        help="Run bounded autonomous discovery and queue execution cycles.",
    )
    parser.add_argument(
        "--discover-tasks",
        action="store_true",
        help="Discover candidate development tasks from the repository.",
    )
    parser.add_argument(
        "--output-queue",
        default=None,
        help="Optional path where discovered tasks should be written as a queue file.",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=3,
        help="Maximum number of autonomous loop cycles.",
    )
    parser.add_argument(
        "--max-tasks-per-cycle",
        type=int,
        default=5,
        help="Maximum number of queued tasks per autonomous cycle.",
    )
    parser.add_argument(
        "--queue-dir",
        default="tasks",
        help="Directory where autonomous loop queue files should be written.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a persisted queue state in queue mode.",
    )
    parser.add_argument(
        "--state-path",
        default=None,
        help="Optional explicit path for the queue state file.",
    )
    parser.add_argument(
        "--workdir",
        default=".",
        help="Working directory where commands should run.",
    )
    parser.add_argument(
        "--no-codex",
        action="store_true",
        help="Skip Codex subprocess execution.",
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Skip local tests/checks execution.",
    )
    parser.add_argument(
        "--codex-command",
        default=None,
        help="Codex command template (supports {prompt} placeholder).",
    )
    parser.add_argument(
        "--codex-timeout",
        type=int,
        default=1800,
        help="Timeout in seconds for Codex subprocess.",
    )
    parser.add_argument(
        "--codex-prompt-arg",
        action="store_true",
        help="Pass prompt as command argument instead of stdin.",
    )
    parser.add_argument(
        "--test-command",
        action="append",
        default=[],
        help="Custom local test/check command, can be repeated.",
    )
    parser.add_argument(
        "--indent",
        type=int,
        default=2,
        help="JSON indent for output.",
    )
    return parser.parse_args()


def main() -> int:
    """Run orchestrator workflow from CLI and print structured JSON output."""

    args = _parse_args()
    if args.auto_loop:
        result: AutoLoopResult = run_autonomous_development_loop(
            workdir=args.workdir,
            max_cycles=args.max_cycles,
            max_tasks_per_cycle=args.max_tasks_per_cycle,
            queue_dir=args.queue_dir,
            run_codex=0 if args.no_codex else 1,
            run_tests=0 if args.no_tests else 1,
            codex_command=args.codex_command,
            codex_timeout_seconds=args.codex_timeout,
            codex_prompt_via_stdin=0 if args.codex_prompt_arg else 1,
        )
        print(result.model_dump_json(indent=args.indent))
        made_progress: bool = any(
            (
                cycle.queue_result.get("summary", {}).get("succeeded", 0) > 0
                or cycle.queue_result.get("summary", {}).get("ready_for_pr", 0) > 0
            )
            for cycle in result.cycles
        )
        return 0 if made_progress else 1

    if args.discover_tasks:
        result: DiscoveryResult = run_task_discovery(
            repo_path=args.workdir,
            output_queue_path=args.output_queue,
        )
        print(result.model_dump_json(indent=args.indent))
        return 0 if result.tasks else 1

    if args.queue:
        result: QueueRunResult = run_development_queue(
            queue_path=args.queue,
            default_workdir=args.workdir,
            default_run_codex=0 if args.no_codex else 1,
            default_run_tests=0 if args.no_tests else 1,
            default_codex_command=args.codex_command,
            default_codex_timeout_seconds=args.codex_timeout,
            default_codex_prompt_via_stdin=0 if args.codex_prompt_arg else 1,
            resume=1 if args.resume else 0,
            state_path=args.state_path,
        )
        print(result.model_dump_json(indent=args.indent))
        summary: dict = result.summary
        return 0 if summary.get("succeeded", 0) > 0 or summary.get("ready_for_pr", 0) > 0 else 1

    task_text: str = " ".join(args.task).strip()
    if not task_text:
        task_text = input("Task goal: ").strip()

    request = DevTaskRequest(
        task=task_text,
        workdir=args.workdir,
        run_codex=0 if args.no_codex else 1,
        run_tests=0 if args.no_tests else 1,
        codex_command=args.codex_command,
        codex_timeout_seconds=args.codex_timeout,
        codex_prompt_via_stdin=0 if args.codex_prompt_arg else 1,
        test_commands=args.test_command,
    )
    result = run_development_task(request)
    print(result.model_dump_json(indent=args.indent))
    return 0 if result.success == 1 else 1


if __name__ == "__main__":
    sys.exit(main())
