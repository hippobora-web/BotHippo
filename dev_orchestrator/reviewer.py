"""Deterministic diff reviewer for the local development orchestrator."""

from __future__ import annotations

import re
import subprocess

from dev_orchestrator.schemas import (
    PRMetadata,
    ReviewResult,
    ReviewerNarrative,
    ScopeEvaluation,
    ScopeRule,
)


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


def _has_blocked_marker(path: str) -> bool:
    """Detect clearly blocked or sensitive path markers."""

    lowered: str = path.lower()
    blocked_markers: tuple[str, ...] = (
        ".env",
        "secret",
        "secrets",
        ".pem",
        ".key",
        "credential",
        "token",
    )
    return any(marker in lowered for marker in blocked_markers)


def _matches_any_prefix(path: str, prefixes: list[str]) -> bool:
    """Return 1-like truth when path matches any configured prefix."""

    return any(path.startswith(prefix) for prefix in prefixes)


def _normalize_task_text(task: str) -> str:
    """Normalize task text for deterministic derived outputs."""

    return " ".join(task.strip().split())


def _title_from_task(task: str) -> str:
    """Build a concise GitHub-style title from task text."""

    normalized: str = _normalize_task_text(task)
    if not normalized:
        return "feat: update task"

    conventional_prefixes: tuple[str, ...] = (
        "feat:",
        "fix:",
        "chore:",
        "refactor:",
        "docs:",
        "test:",
    )
    lowered: str = normalized.lower()
    if any(lowered.startswith(prefix) for prefix in conventional_prefixes):
        title: str = normalized
    else:
        title = f"feat: {normalized}"
    return title[:72].rstrip()


def _risk_flag_message(risk_flag: str) -> str:
    """Expand one deterministic risk flag into human-readable text."""

    mapping: dict[str, str] = {
        "no_changes_detected": "No file changes were detected.",
        "large_change_file_count": "The diff touches a large number of files.",
        "large_change_insertions": "The diff adds a large number of lines.",
        "sensitive_or_deployment_changes": "The diff includes sensitive or deployment-oriented paths.",
        "out_of_scope_changes": "Some changed files are outside the expected task scope.",
        "blocked_path_changes": "Some changed files are in blocked or sensitive paths.",
        "preexisting_repo_changes": "The repository already contained changes before the run started.",
    }
    return mapping.get(risk_flag, f"Risk flag raised: {risk_flag}.")


def _scope_status_text(review_result: ReviewResult) -> str:
    """Return a short human-readable scope status."""

    if review_result.blocked_files:
        return "Scope validation failed due to blocked files."
    if review_result.out_of_scope_files:
        return "Scope validation failed due to out-of-scope files."
    if review_result.allowed_files:
        return "Scope respected."
    return "No explicit scope constraint was triggered."


def _risk_summary_text(review_result: ReviewResult) -> str:
    """Return a compact human-readable risk summary."""

    blocking_risks: list[str] = [
        risk_flag for risk_flag in review_result.risk_flags if risk_flag != "no_changes_detected"
    ]
    if blocking_risks:
        return "Blocking risks: " + ", ".join(blocking_risks)
    if review_result.risk_flags:
        return "Non-blocking risks: " + ", ".join(review_result.risk_flags)
    return "No review risks detected."


def infer_scope_rule(task: str) -> ScopeRule:
    """Infer a deterministic scope rule from task text."""

    task_lower: str = task.lower()
    blocked_prefixes: list[str] = [".env", "logs/", ".git/"]

    orchestrator_terms: tuple[str, ...] = (
        "dev orchestrator",
        "orchestrator",
        "codex runner",
        "reviewer",
        "planner",
    )
    evengine_terms: tuple[str, ...] = (
        "risk",
        "portfolio",
        "quant",
        "analysis",
        "evengine",
    )

    if any(term in task_lower for term in orchestrator_terms):
        return ScopeRule(
            label="dev_orchestrator_scope",
            allowed_prefixes=["dev_orchestrator/", "run_dev_agent.py"],
            blocked_prefixes=blocked_prefixes,
        )
    if any(term in task_lower for term in evengine_terms):
        return ScopeRule(
            label="evengine_scope",
            allowed_prefixes=["evengine/"],
            blocked_prefixes=blocked_prefixes,
        )
    return ScopeRule(
        label="open_scope",
        allowed_prefixes=[],
        blocked_prefixes=blocked_prefixes,
    )


def evaluate_scope(
    *,
    changed_files: list[str],
    scope_rule: ScopeRule,
) -> ScopeEvaluation:
    """Evaluate changed files against deterministic scope rules."""

    allowed_files: list[str] = []
    out_of_scope_files: list[str] = []
    blocked_files: list[str] = []

    for path in changed_files:
        if _matches_any_prefix(path, scope_rule.blocked_prefixes) or _has_blocked_marker(path):
            blocked_files.append(path)
            continue

        if not scope_rule.allowed_prefixes or _matches_any_prefix(path, scope_rule.allowed_prefixes):
            allowed_files.append(path)
            continue

        out_of_scope_files.append(path)

    ok: int = 1 if not blocked_files and not out_of_scope_files else 0
    summary: str = (
        f"scope={scope_rule.label} allowed={len(allowed_files)} "
        f"out_of_scope={len(out_of_scope_files)} blocked={len(blocked_files)}"
    )
    return ScopeEvaluation(
        ok=ok,
        allowed_files=allowed_files,
        out_of_scope_files=out_of_scope_files,
        blocked_files=blocked_files,
        summary=summary,
    )


def build_reviewer_narrative(review_result: ReviewResult) -> ReviewerNarrative:
    """Build a deterministic human-readable review narrative."""

    changed_file_count: int = len(review_result.changed_files)
    blocked_state: str = (
        f"Blocked files detected: {len(review_result.blocked_files)}."
        if review_result.blocked_files
        else "No blocked files detected."
    )
    review_state: str = "Review status: pass." if review_result.ok == 1 else "Review status: attention required."
    summary: str = (
        f"Reviewed {changed_file_count} changed files. "
        f"{_scope_status_text(review_result)} "
        f"{blocked_state} "
        f"{review_state} "
        f"{_risk_summary_text(review_result)}"
    )
    warnings: list[str] = [_risk_flag_message(risk_flag) for risk_flag in review_result.risk_flags]
    return ReviewerNarrative(
        summary=summary,
        notable_changes=review_result.changed_files[:10],
        warnings=warnings,
    )


def build_pr_metadata(
    *,
    task: str,
    review_result: ReviewResult,
) -> PRMetadata:
    """Build deterministic suggested PR metadata from task and review."""

    suggested_title: str = _title_from_task(task)
    change_scope_summary: str = _scope_status_text(review_result)
    risk_summary: str = _risk_summary_text(review_result)

    changed_count: int = len(review_result.changed_files)
    if review_result.allowed_files:
        affected_scope: str = ", ".join(review_result.allowed_files[:10])
    else:
        affected_scope = ", ".join(review_result.changed_files[:10]) or "no changed files detected"

    suggested_description: str = "\n".join(
        [
            f"Update task: {_normalize_task_text(task) or 'unspecified task'}",
            f"- affected files: {changed_count}",
            f"- main scope: {affected_scope}",
            f"- review status: {'pass' if review_result.ok == 1 else 'attention required'}",
            f"- risk status: {risk_summary}",
            f"- scope status: {change_scope_summary}",
        ]
    )

    return PRMetadata(
        suggested_title=suggested_title,
        suggested_description=suggested_description,
        change_scope_summary=change_scope_summary,
        risk_summary=risk_summary,
    )


def review_changes(repo_path: str, task: str | None = None) -> ReviewResult:
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

    scope_evaluation: ScopeEvaluation | None = None
    if task is not None:
        scope_rule: ScopeRule = infer_scope_rule(task)
        scope_evaluation = evaluate_scope(
            changed_files=changed_files,
            scope_rule=scope_rule,
        )
        if scope_evaluation.out_of_scope_files:
            risk_flags.append("out_of_scope_changes")
        if scope_evaluation.blocked_files:
            risk_flags.append("blocked_path_changes")

    blocking_risk_flags: list[str] = [
        risk_flag for risk_flag in risk_flags if risk_flag != "no_changes_detected"
    ]
    if scope_evaluation is not None and scope_evaluation.ok == 0:
        blocking_risk_flags.append("scope_validation_failed")
    ok: int = 1 if not blocking_risk_flags else 0
    return ReviewResult(
        ok=ok,
        summary=summary,
        changed_files=changed_files,
        risk_flags=risk_flags,
        allowed_files=[] if scope_evaluation is None else scope_evaluation.allowed_files,
        out_of_scope_files=[] if scope_evaluation is None else scope_evaluation.out_of_scope_files,
        blocked_files=[] if scope_evaluation is None else scope_evaluation.blocked_files,
    )
