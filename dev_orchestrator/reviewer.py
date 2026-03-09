"""Deterministic diff reviewer for the local development orchestrator."""

from __future__ import annotations

import re
import subprocess

from dev_orchestrator.schemas import ReviewResult


def _run_git(args: list[str], repo_path: str) -> str:
    """Run git command and return stdout or empty string on failure."""

    try:
        completed: subprocess.CompletedProcess[str] = subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return ""
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def _collect_changed_files(repo_path: str) -> list[str]:
    """Collect changed tracked and untracked files deterministically."""

    diff_names: set[str] = set(
        line for line in _run_git(["diff", "--name-only"], repo_path).splitlines() if line
    )
    staged_names: set[str] = set(
        line for line in _run_git(["diff", "--cached", "--name-only"], repo_path).splitlines() if line
    )
    untracked_names: set[str] = set(
        line
        for line in _run_git(["ls-files", "--others", "--exclude-standard"], repo_path).splitlines()
        if line
    )
    return sorted(diff_names | staged_names | untracked_names)


def _parse_inserted_lines(diff_stat: str) -> int:
    """Parse inserted line count from git diff stat or shortstat text."""

    match = re.search(r"(\d+)\s+insertions?\(\+\)", diff_stat)
    if match is None:
        return 0
    return int(match.group(1))


def _has_sensitive_path(path: str) -> bool:
    """Detect sensitive or deployment-oriented files by path."""

    lowered: str = path.lower()
    sensitive_terms: tuple[str, ...] = (
        ".env",
        "secret",
        "secrets",
        "deploy",
        "deployment",
        ".pem",
        ".key",
    )
    return any(term in lowered for term in sensitive_terms)


def review_changes(repo_path: str) -> ReviewResult:
    """Review local git changes and return deterministic risk assessment."""

    changed_files: list[str] = _collect_changed_files(repo_path)
    diff_stat: str = _run_git(["diff", "--stat"], repo_path)
    staged_diff_stat: str = _run_git(["diff", "--cached", "--stat"], repo_path)
    untracked_count: int = len(
        _run_git(["ls-files", "--others", "--exclude-standard"], repo_path).splitlines()
    )

    combined_summary_parts: list[str] = []
    if diff_stat:
        combined_summary_parts.append(diff_stat)
    if staged_diff_stat and staged_diff_stat != diff_stat:
        combined_summary_parts.append(staged_diff_stat)
    if untracked_count > 0:
        combined_summary_parts.append(f"untracked files: {untracked_count}")
    summary: str = "\n".join(part for part in combined_summary_parts if part).strip()
    if not summary:
        summary = "no diff summary available"

    inserted_lines: int = _parse_inserted_lines(summary)
    risk_flags: list[str] = []
    if not changed_files:
        risk_flags.append("no_changes_detected")
    if len(changed_files) > 20:
        risk_flags.append("large_change_file_count")
    if inserted_lines > 800:
        risk_flags.append("large_change_insertions")
    if any(_has_sensitive_path(path) for path in changed_files):
        risk_flags.append("sensitive_or_deployment_changes")

    blocking_risk_flags: list[str] = [
        risk_flag for risk_flag in risk_flags if risk_flag != "no_changes_detected"
    ]
    ok: int = 1 if not blocking_risk_flags else 0
    return ReviewResult(
        ok=ok,
        summary=summary,
        changed_files=changed_files,
        risk_flags=risk_flags,
    )
