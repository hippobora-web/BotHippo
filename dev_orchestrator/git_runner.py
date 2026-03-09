"""Git utilities for branching, commit, push, and repository summaries."""

from __future__ import annotations

import re
import subprocess

from dev_orchestrator.schemas import GitActionResult, GitSummary


def _run_git(args: list[str], repo_path: str) -> subprocess.CompletedProcess[str]:
    """Run a git command without raising exceptions."""

    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        return subprocess.CompletedProcess(
            args=["git", *args],
            returncode=1,
            stdout="",
            stderr=f"git_execution_failed:{exc.__class__.__name__}",
        )


def _trim_output(text: str, limit: int = 20000) -> str:
    """Trim long git output to bounded size."""

    if len(text) <= limit:
        return text
    head: str = text[: limit // 2]
    tail: str = text[-(limit // 2) :]
    return f"{head}\n...[truncated]...\n{tail}"


def _current_branch(repo_path: str) -> str:
    """Return current branch name or empty string."""

    completed: subprocess.CompletedProcess[str] = _run_git(
        ["rev-parse", "--abbrev-ref", "HEAD"],
        repo_path,
    )
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def is_repo_clean(repo_path: str) -> int:
    """Return 1 when the repository has no tracked or untracked changes."""

    completed: subprocess.CompletedProcess[str] = _run_git(
        ["status", "--porcelain"],
        repo_path,
    )
    if completed.returncode != 0:
        return 0
    return 1 if not completed.stdout.strip() else 0


def _slugify_goal(goal: str) -> str:
    """Create a deterministic branch slug from task goal."""

    slug: str = re.sub(r"[^a-z0-9]+", "-", goal.strip().lower())
    slug = slug.strip("-")
    if not slug:
        slug = "task"
    return slug[:48].strip("-") or "task"


def _branch_exists(repo_path: str, branch_name: str) -> int:
    """Return 1 when a local branch already exists."""

    completed: subprocess.CompletedProcess[str] = _run_git(
        ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        repo_path,
    )
    return 1 if completed.returncode == 0 else 0


def _unique_branch_name(repo_path: str, goal: str) -> str:
    """Generate a unique local branch name for the task."""

    base_name: str = f"auto/{_slugify_goal(goal)}"
    if _branch_exists(repo_path, base_name) == 0:
        return base_name

    index: int = 2
    while True:
        candidate: str = f"{base_name}-{index}"
        if _branch_exists(repo_path, candidate) == 0:
            return candidate
        index += 1


def _stdout(result: subprocess.CompletedProcess[str]) -> str:
    """Return trimmed stdout from subprocess result."""

    return _trim_output(result.stdout.strip())


def _stderr(result: subprocess.CompletedProcess[str]) -> str:
    """Return trimmed stderr from subprocess result."""

    return _trim_output(result.stderr.strip())


def create_task_branch(repo_path: str, goal: str) -> GitActionResult:
    """Create a task branch from current HEAD."""

    branch_name: str = _unique_branch_name(repo_path, goal)
    completed: subprocess.CompletedProcess[str] = _run_git(
        ["checkout", "-b", branch_name],
        repo_path,
    )
    return GitActionResult(
        ok=1 if completed.returncode == 0 else 0,
        branch_name=branch_name,
        stdout=_stdout(completed),
        stderr=_stderr(completed),
    )


def commit_all_changes(
    repo_path: str,
    message: str,
    *,
    allow_full_stage: bool = False,
) -> GitActionResult:
    """Stage and commit current repository changes when the run is safe."""

    branch_name: str = _current_branch(repo_path)
    if not allow_full_stage:
        return GitActionResult(
            ok=0,
            branch_name=branch_name,
            stderr="unsafe_to_stage_all_changes",
        )

    status_result: subprocess.CompletedProcess[str] = _run_git(["status", "--porcelain"], repo_path)
    if status_result.returncode != 0 or not status_result.stdout.strip():
        return GitActionResult(
            ok=0,
            branch_name=branch_name,
            stdout=_stdout(status_result),
            stderr="no_changes_to_commit",
        )

    add_result: subprocess.CompletedProcess[str] = _run_git(["add", "-A"], repo_path)
    if add_result.returncode != 0:
        return GitActionResult(
            ok=0,
            branch_name=branch_name,
            stdout=_stdout(add_result),
            stderr=_stderr(add_result),
        )

    commit_result: subprocess.CompletedProcess[str] = _run_git(["commit", "-m", message], repo_path)
    commit_sha: str = ""
    if commit_result.returncode == 0:
        sha_result: subprocess.CompletedProcess[str] = _run_git(["rev-parse", "HEAD"], repo_path)
        commit_sha = sha_result.stdout.strip() if sha_result.returncode == 0 else ""

    return GitActionResult(
        ok=1 if commit_result.returncode == 0 else 0,
        branch_name=branch_name,
        commit_sha=commit_sha,
        stdout=_stdout(commit_result),
        stderr=_stderr(commit_result),
    )


def push_branch(repo_path: str, branch_name: str) -> GitActionResult:
    """Push branch to origin without merging."""

    push_result: subprocess.CompletedProcess[str] = _run_git(
        ["push", "-u", "origin", branch_name],
        repo_path,
    )
    return GitActionResult(
        ok=1 if push_result.returncode == 0 else 0,
        branch_name=branch_name,
        stdout=_stdout(push_result),
        stderr=_stderr(push_result),
    )


def collect_git_summary(workdir: str) -> GitSummary:
    """Collect compact git status and diff information."""

    is_git_repo_result: subprocess.CompletedProcess[str] = _run_git(
        ["rev-parse", "--is-inside-work-tree"],
        workdir,
    )
    is_git_repo: int = 1 if is_git_repo_result.returncode == 0 and is_git_repo_result.stdout.strip() == "true" else 0
    if is_git_repo == 0:
        return GitSummary(is_git_repo=0)

    changed_files_result: subprocess.CompletedProcess[str] = _run_git(["diff", "--name-only"], workdir)
    changed_files: list[str] = [
        line for line in changed_files_result.stdout.splitlines() if line.strip()
    ]
    return GitSummary(
        is_git_repo=1,
        branch=_current_branch(workdir),
        status_short=_stdout(_run_git(["status", "--short", "--branch"], workdir)),
        diff_stat=_stdout(_run_git(["diff", "--stat"], workdir)),
        staged_diff_stat=_stdout(_run_git(["diff", "--cached", "--stat"], workdir)),
        changed_files=changed_files,
    )
