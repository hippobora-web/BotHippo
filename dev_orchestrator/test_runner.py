"""Local checks/test execution utilities for the development orchestrator."""

from __future__ import annotations

import glob
import os
import subprocess
import time

from dev_orchestrator.schemas import TestCheckResult, TestRunResult


def _trim_output(text: str, limit: int = 30000) -> str:
    """Trim captured command output to a bounded size."""

    if len(text) <= limit:
        return text
    head: str = text[: limit // 2]
    tail: str = text[-(limit // 2) :]
    return f"{head}\n...[truncated]...\n{tail}"


def _has_pytest_targets(workdir: str) -> int:
    """Return 1 when pytest-style test targets are detected."""

    patterns: list[str] = [
        "tests",
        "test_*.py",
        "*_test.py",
        "**/test_*.py",
        "**/*_test.py",
    ]
    for pattern in patterns:
        matches: list[str] = glob.glob(os.path.join(workdir, pattern), recursive=True)
        if matches:
            return 1
    return 0


def _default_check_commands(workdir: str) -> list[tuple[str, str]]:
    """Build default local checks list."""

    checks: list[tuple[str, str]] = [("python_compile", "python3 -m compileall -q .")]
    if _has_pytest_targets(workdir) == 1:
        checks.append(("pytest", "pytest -q"))
    return checks


def _run_shell_check(*, name: str, command: str, workdir: str) -> TestCheckResult:
    """Run one shell check and return structured result."""

    started: float = time.monotonic()
    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=workdir,
            check=False,
        )
        duration: float = time.monotonic() - started
        return TestCheckResult(
            name=name,
            command=command,
            return_code=completed.returncode,
            success=1 if completed.returncode == 0 else 0,
            stdout=_trim_output(completed.stdout),
            stderr=_trim_output(completed.stderr),
            duration_seconds=duration,
        )
    except Exception as exc:
        duration = time.monotonic() - started
        return TestCheckResult(
            name=name,
            command=command,
            return_code=1,
            success=0,
            stderr=f"check_execution_failed:{exc.__class__.__name__}",
            duration_seconds=duration,
        )


def run_local_checks(*, workdir: str, commands: list[str] | None = None) -> TestRunResult:
    """Run local checks and return an aggregated structured result."""

    checks_to_run: list[tuple[str, str]]
    if commands:
        checks_to_run = [(f"custom_check_{index+1}", command) for index, command in enumerate(commands)]
    else:
        checks_to_run = _default_check_commands(workdir)

    check_results: list[TestCheckResult] = [
        _run_shell_check(name=name, command=command, workdir=workdir)
        for name, command in checks_to_run
    ]

    all_passed: int = 1 if all(check.success == 1 for check in check_results) else 0
    return TestRunResult(
        attempted=1,
        all_passed=all_passed,
        checks=check_results,
    )

