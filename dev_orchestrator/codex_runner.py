"""Subprocess wrapper to execute Codex from the local orchestrator."""

from __future__ import annotations

import shlex
import subprocess
import time

from dev_orchestrator.schemas import CodexRunResult


def _trim_output(text: str, limit: int = 40000) -> str:
    """Trim captured command output to a bounded size."""

    if len(text) <= limit:
        return text
    head: str = text[: limit // 2]
    tail: str = text[-(limit // 2) :]
    return f"{head}\n...[truncated]...\n{tail}"


def _build_command(command_template: str, prompt: str, prompt_via_stdin: int) -> list[str]:
    """Build subprocess command from a template and prompt."""

    command_parts: list[str] = shlex.split(command_template)
    if not command_parts:
        return []

    has_prompt_placeholder: bool = any("{prompt}" in part for part in command_parts)
    if has_prompt_placeholder:
        return [part.replace("{prompt}", prompt) for part in command_parts]
    if prompt_via_stdin == 1:
        return command_parts
    return [*command_parts, prompt]


def run_codex_prompt(
    *,
    prompt: str,
    workdir: str,
    command_template: str,
    timeout_seconds: int,
    prompt_via_stdin: int = 1,
) -> CodexRunResult:
    """Run Codex command locally and return a structured execution result."""

    command: list[str] = _build_command(command_template, prompt, prompt_via_stdin)
    if not command:
        return CodexRunResult(
            attempted=1,
            ok=0,
            success=0,
            command=[],
            error_message="empty_codex_command",
        )

    started: float = time.monotonic()
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            input=prompt if prompt_via_stdin == 1 else None,
            text=True,
            capture_output=True,
            cwd=workdir,
            timeout=timeout_seconds,
            check=False,
        )
        duration: float = time.monotonic() - started
        success: int = 1 if completed.returncode == 0 else 0
        return CodexRunResult(
            attempted=1,
            ok=success,
            success=success,
            command=command,
            return_code=completed.returncode,
            stdout=_trim_output(completed.stdout),
            stderr=_trim_output(completed.stderr),
            duration_seconds=duration,
        )
    except FileNotFoundError:
        duration = time.monotonic() - started
        return CodexRunResult(
            attempted=1,
            ok=0,
            success=0,
            command=command,
            error_message="codex_command_not_found",
            duration_seconds=duration,
        )
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - started
        return CodexRunResult(
            attempted=1,
            ok=0,
            success=0,
            command=command,
            error_message="codex_command_timeout",
            stdout=_trim_output(exc.stdout or ""),
            stderr=_trim_output(exc.stderr or ""),
            duration_seconds=duration,
        )
    except Exception as exc:
        duration = time.monotonic() - started
        return CodexRunResult(
            attempted=1,
            ok=0,
            success=0,
            command=command,
            error_message=f"codex_command_failed:{exc.__class__.__name__}",
            duration_seconds=duration,
        )
