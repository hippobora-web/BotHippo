"""CLI entrypoint for the local development orchestrator."""

from __future__ import annotations

import argparse
import sys

from dev_orchestrator.schemas import DevTaskRequest
from dev_orchestrator.supervisor import run_development_task


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the development orchestrator."""

    parser = argparse.ArgumentParser(description="Run local dev orchestrator workflow.")
    parser.add_argument("task", nargs="*", help="Development task description.")
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
