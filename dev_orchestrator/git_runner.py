"""Git summary utilities for local development orchestrator runs."""

from __future__ import annotations

import subprocess

from dev_orchestrator.schemas import GitSummary


def _run_git_command(args: list[str], workdir: str) -> str:
    """Run a git command and return stdout or empty string on failure."""

    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            ["git", *args],
            cwd=workdir,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def collect_git_summary(workdir: str) -> GitSummary:
    """Collect compact git status and diff information."""

    is_git_repo_output: str = _run_git_command(["rev-parse", "--is-inside-work-tree"], workdir)
    is_git_repo: int = 1 if is_git_repo_output == "true" else 0
    if is_git_repo == 0:
        return GitSummary(is_git_repo=0)

    changed_files_output: str = _run_git_command(["diff", "--name-only"], workdir)
    changed_files: list[str] = [line for line in changed_files_output.splitlines() if line]
    return GitSummary(
        is_git_repo=1,
        branch=_run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], workdir),
        status_short=_run_git_command(["status", "--short", "--branch"], workdir),
        diff_stat=_run_git_command(["diff", "--stat"], workdir),
        staged_diff_stat=_run_git_command(["diff", "--cached", "--stat"], workdir),
        changed_files=changed_files,
    )

