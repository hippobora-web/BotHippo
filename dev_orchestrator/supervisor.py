"""Supervisor for local development task orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from dev_orchestrator.codex_runner import run_codex_prompt
from dev_orchestrator.git_runner import (
    collect_git_summary,
    commit_all_changes,
    create_task_branch,
    is_repo_clean,
    push_branch,
)
from dev_orchestrator.planner import build_codex_prompt, build_execution_plan
from dev_orchestrator.reviewer import review_changes
from dev_orchestrator.schemas import (
    CodexRunResult,
    DevRunResult,
    DevTaskRequest,
    GitActionResult,
    ReviewResult,
    TestRunResult,
)
from dev_orchestrator.test_runner import run_local_checks


def _skipped_codex_result() -> CodexRunResult:
    """Return structured result when Codex execution is skipped."""

    return CodexRunResult(
        attempted=0,
        ok=1,
        success=1,
        error_message="codex_skipped",
    )


def _empty_test_result() -> TestRunResult:
    """Return structured result when tests are skipped."""

    return TestRunResult(
        attempted=0,
        all_passed=1,
        checks=[],
    )


def _default_review_result(summary: str) -> ReviewResult:
    """Create a default review result for early-return paths."""

    return ReviewResult(
        ok=0,
        summary=summary,
        changed_files=[],
        risk_flags=[],
    )


def _combine_git_actions(*actions: GitActionResult) -> GitActionResult:
    """Combine several git action results into one structured summary."""

    non_empty_actions: list[GitActionResult] = list(actions)
    branch_name: str = next((action.branch_name for action in non_empty_actions if action.branch_name), "")
    commit_sha: str = next((action.commit_sha for action in reversed(non_empty_actions) if action.commit_sha), "")
    ok: int = 1 if non_empty_actions and all(action.ok == 1 for action in non_empty_actions) else 0
    stdout_parts: list[str] = [action.stdout for action in non_empty_actions if action.stdout]
    stderr_parts: list[str] = [action.stderr for action in non_empty_actions if action.stderr]
    return GitActionResult(
        ok=ok,
        branch_name=branch_name,
        commit_sha=commit_sha,
        stdout="\n".join(stdout_parts),
        stderr="\n".join(stderr_parts),
    )


def _commit_message(task: str) -> str:
    """Build a deterministic automatic commit message."""

    normalized: str = " ".join(task.strip().split())
    short_message: str = normalized[:72].strip()
    if not short_message:
        short_message = "task update"
    return f"auto: {short_message}"


def _merge_recommendation(*, codex_ok: int, review_ok: int, tests_ok: int) -> str:
    """Compute merge recommendation from orchestrator outcomes."""

    if codex_ok == 1 and review_ok == 1 and tests_ok == 1:
        return "ready_for_pr"
    if codex_ok == 1:
        return "needs_review"
    return "failed"


def run_development_task(request: DevTaskRequest) -> DevRunResult:
    """Run the end-to-end local development orchestrator workflow."""

    started_at: str = datetime.now(timezone.utc).isoformat()
    repo_was_clean: int = is_repo_clean(request.workdir)

    branch_result: GitActionResult = create_task_branch(request.workdir, request.task)
    plan = build_execution_plan(request.task)
    codex_prompt: str = build_codex_prompt(request.task, plan)

    if branch_result.ok == 0:
        git_summary = collect_git_summary(request.workdir)
        finished_at: str = datetime.now(timezone.utc).isoformat()
        review_result: ReviewResult = _default_review_result("branch_creation_failed")
        git_action_result: GitActionResult = branch_result
        merge_recommendation: str = "failed"
        return DevRunResult(
            task=request.task,
            workdir=request.workdir,
            started_at=started_at,
            finished_at=finished_at,
            plan=plan,
            codex=_skipped_codex_result(),
            tests=_empty_test_result(),
            review_result=review_result.model_dump(),
            git_action_result=git_action_result.model_dump(),
            git=git_summary,
            branch_name=branch_result.branch_name,
            merge_recommendation=merge_recommendation,
            success=0,
        )

    codex_result: CodexRunResult
    if request.run_codex == 1:
        command_template: str = request.codex_command or "codex"
        codex_result = run_codex_prompt(
            prompt=codex_prompt,
            workdir=request.workdir,
            command_template=command_template,
            timeout_seconds=request.codex_timeout_seconds,
            prompt_via_stdin=request.codex_prompt_via_stdin,
        )
    else:
        codex_result = _skipped_codex_result()

    review_result = review_changes(request.workdir)
    if repo_was_clean == 0:
        updated_flags: list[str] = list(review_result.risk_flags)
        if "preexisting_repo_changes" not in updated_flags:
            updated_flags.append("preexisting_repo_changes")
        review_result = review_result.model_copy(
            update={
                "ok": 0,
                "risk_flags": updated_flags,
            }
        )

    test_result: TestRunResult
    if request.run_tests == 1:
        test_result = run_local_checks(workdir=request.workdir, commands=request.test_commands)
    else:
        test_result = _empty_test_result()

    git_action_result: GitActionResult = branch_result
    if review_result.ok == 1 and codex_result.ok == 1 and repo_was_clean == 1:
        commit_result: GitActionResult = commit_all_changes(
            request.workdir,
            _commit_message(request.task),
            allow_full_stage=True,
        )
        push_result: GitActionResult
        if commit_result.ok == 1:
            push_result = push_branch(request.workdir, branch_result.branch_name)
        else:
            push_result = GitActionResult(
                ok=0,
                branch_name=branch_result.branch_name,
                commit_sha=commit_result.commit_sha,
                stderr="push_skipped_due_to_commit_failure",
            )
        git_action_result = _combine_git_actions(branch_result, commit_result, push_result)
    elif repo_was_clean == 0:
        git_action_result = _combine_git_actions(
            branch_result,
            GitActionResult(
                ok=0,
                branch_name=branch_result.branch_name,
                stderr="preexisting_repo_changes",
            ),
        )

    git_summary = collect_git_summary(request.workdir)
    finished_at: str = datetime.now(timezone.utc).isoformat()

    merge_recommendation: str = _merge_recommendation(
        codex_ok=codex_result.ok,
        review_ok=review_result.ok,
        tests_ok=test_result.all_passed,
    )
    success: int = 1 if merge_recommendation == "ready_for_pr" else 0

    return DevRunResult(
        task=request.task,
        workdir=request.workdir,
        started_at=started_at,
        finished_at=finished_at,
        plan=plan,
        codex=codex_result,
        tests=test_result,
        review_result=review_result.model_dump(),
        git_action_result=git_action_result.model_dump(),
        git=git_summary,
        branch_name=branch_result.branch_name,
        merge_recommendation=merge_recommendation,
        success=success,
    )
