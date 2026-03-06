"""GitHub pull request helpers using the GitHub CLI."""

from __future__ import annotations

import json
import re
import subprocess
from typing import Any


def _extract_url(text: str) -> str:
    """Extract the first URL from a command output string."""

    match = re.search(r"https?://\S+", text)
    if match is None:
        return ""
    return match.group(0).rstrip(").,")


def _run_gh(args: list[str], repo_path: str) -> subprocess.CompletedProcess[str]:
    """Run a gh command and capture its output without raising."""

    try:
        return subprocess.run(
            ["gh", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(
            args=["gh", *args],
            returncode=127,
            stdout="",
            stderr="gh_not_installed",
        )
    except Exception as exc:
        return subprocess.CompletedProcess(
            args=["gh", *args],
            returncode=1,
            stdout="",
            stderr=f"gh_execution_failed:{exc.__class__.__name__}",
        )


def _find_existing_pr_url(*, repo_path: str, branch_name: str) -> str:
    """Find an existing pull request URL for the branch when available."""

    result: subprocess.CompletedProcess[str] = _run_gh(
        [
            "pr",
            "list",
            "--head",
            branch_name,
            "--base",
            "main",
            "--state",
            "open",
            "--json",
            "url",
        ],
        repo_path,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ""

    try:
        payload: Any = json.loads(result.stdout)
    except json.JSONDecodeError:
        return _extract_url(result.stdout)

    if isinstance(payload, list) and payload:
        first_item: Any = payload[0]
        if isinstance(first_item, dict):
            url: Any = first_item.get("url")
            return url if isinstance(url, str) else ""
    return ""


def create_pull_request(
    *,
    repo_path: str,
    branch_name: str,
    title: str,
    body: str,
) -> tuple[int, str]:
    """Create a GitHub pull request or return an existing PR URL."""

    create_result: subprocess.CompletedProcess[str] = _run_gh(
        [
            "pr",
            "create",
            "--title",
            title,
            "--body",
            body,
            "--head",
            branch_name,
            "--base",
            "main",
        ],
        repo_path,
    )

    if create_result.returncode == 0:
        pr_url: str = _extract_url(create_result.stdout) or _extract_url(create_result.stderr)
        if pr_url:
            return 1, pr_url
        existing_pr_url: str = _find_existing_pr_url(
            repo_path=repo_path,
            branch_name=branch_name,
        )
        return (1, existing_pr_url) if existing_pr_url else (0, "")

    existing_pr_url = _find_existing_pr_url(
        repo_path=repo_path,
        branch_name=branch_name,
    )
    if existing_pr_url:
        return 1, existing_pr_url

    return 0, ""


def merge_pull_request(
    *,
    repo_path: str,
    pr_url: str,
) -> int:
    """Merge a GitHub pull request with squash strategy and branch deletion."""

    if not pr_url.strip():
        return 0

    merge_result: subprocess.CompletedProcess[str] = _run_gh(
        [
            "pr",
            "merge",
            pr_url,
            "--squash",
            "--delete-branch",
        ],
        repo_path,
    )
    return 1 if merge_result.returncode == 0 else 0
