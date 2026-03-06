"""Supervisor for local development task orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from dev_orchestrator.codex_runner import build_repair_prompt, run_codex_prompt
from dev_orchestrator.git_runner import (
    collect_git_summary,
    commit_all_changes,
    create_task_branch,
    is_repo_clean,
    push_branch,
)
from dev_orchestrator.planner import build_codex_prompt, build_execution_plan
from dev_orchestrator.reviewer import (
    build_pr_metadata,
    build_reviewer_narrative,
    review_changes,
)
from dev_orchestrator.schemas import (
    CodexRunResult,
    DevRunResult,
    DevTaskRequest,
    GitActionResult,
    LoopMetadata,
    PRMetadata,
    RepairAttemptResult,
    ReviewResult,
    ReviewerNarrative,
    ScopeEvaluation,
    TestRunResult,
)
from dev_orchestrator.test_runner import run_local_checks, summarize_failed_checks


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


def _empty_repair_attempt() -> RepairAttemptResult:
    """Return structured result when repair is not attempted."""

    return RepairAttemptResult(
        attempted=0,
        ok=0,
    )


def _default_loop_metadata(loop_status: str) -> LoopMetadata:
    """Return loop metadata for early-return paths."""

    return LoopMetadata(
        initial_pass_ok=0,
        repair_attempted=0,
        repair_ok=0,
        final_pass_ok=0,
        loop_status=loop_status,
    )


def _default_review_result(summary: str) -> ReviewResult:
    """Create a default review result for early-return paths."""

    return ReviewResult(
        ok=0,
        summary=summary,
        changed_files=[],
        risk_flags=[],
    )


def _scope_evaluation_from_review(review_result: ReviewResult) -> ScopeEvaluation:
    """Build scope evaluation metadata from a review result."""

    ok: int = 1 if not review_result.out_of_scope_files and not review_result.blocked_files else 0
    if review_result.allowed_files or review_result.out_of_scope_files or review_result.blocked_files:
        summary: str = (
            f"allowed={len(review_result.allowed_files)} "
            f"out_of_scope={len(review_result.out_of_scope_files)} "
            f"blocked={len(review_result.blocked_files)}"
        )
    else:
        summary = "scope not explicitly constrained"

    return ScopeEvaluation(
        ok=ok,
        allowed_files=review_result.allowed_files,
        out_of_scope_files=review_result.out_of_scope_files,
        blocked_files=review_result.blocked_files,
        summary=summary,
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


def _pass_is_acceptable(
    *,
    codex_result: CodexRunResult,
    review_result: ReviewResult,
    scope_evaluation: ScopeEvaluation,
    test_result: TestRunResult,
) -> int:
    """Return 1 when codex, review, and tests are all acceptable."""

    if (
        codex_result.ok == 1
        and review_result.ok == 1
        and scope_evaluation.ok == 1
        and test_result.all_passed == 1
    ):
        return 1
    return 0


def _trim_prompt_summary(prompt: str, limit: int = 2000) -> str:
    """Trim prompt summary to a deterministic bounded length."""

    return prompt if len(prompt) <= limit else f"{prompt[:limit]}...[truncated]"


def _apply_dirty_repo_flag(review_result: ReviewResult, repo_was_clean: int) -> ReviewResult:
    """Augment review result when the repository was dirty before the run."""

    if repo_was_clean == 1:
        return review_result

    updated_flags: list[str] = list(review_result.risk_flags)
    if "preexisting_repo_changes" not in updated_flags:
        updated_flags.append("preexisting_repo_changes")
    return review_result.model_copy(
        update={
            "ok": 0,
            "risk_flags": updated_flags,
        }
    )


def _final_merge_recommendation(
    *,
    branch_ok: int,
    final_codex_ok: int,
    final_review_ok: int,
    final_tests_ok: int,
    repair_attempted: int,
) -> str:
    """Compute final merge recommendation after optional repair."""

    if branch_ok == 0 or final_codex_ok == 0:
        return "failed"
    if final_review_ok == 1 and final_tests_ok == 1:
        return "ready_for_pr"
    if repair_attempted == 1:
        return "failed_after_repair"
    return "needs_review"


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
        repair_attempt: RepairAttemptResult = _empty_repair_attempt()
        loop_metadata: LoopMetadata = _default_loop_metadata("hard_failure")
        scope_evaluation: ScopeEvaluation = _scope_evaluation_from_review(review_result)
        reviewer_narrative: ReviewerNarrative = build_reviewer_narrative(review_result)
        pr_metadata: PRMetadata = build_pr_metadata(
            task=request.task,
            review_result=review_result,
        )
        merge_recommendation: str = "failed"
        return DevRunResult(
            task=request.task,
            workdir=request.workdir,
            started_at=started_at,
            finished_at=finished_at,
            plan=plan,
            codex=_skipped_codex_result(),
            tests=_empty_test_result(),
            repair_attempt=repair_attempt.model_dump(),
            loop_metadata=loop_metadata.model_dump(),
            scope_evaluation=scope_evaluation.model_dump(),
            pr_metadata=pr_metadata.model_dump(),
            reviewer_narrative=reviewer_narrative.model_dump(),
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

    review_result = _apply_dirty_repo_flag(
        review_changes(request.workdir, request.task),
        repo_was_clean,
    )
    scope_evaluation: ScopeEvaluation = _scope_evaluation_from_review(review_result)

    test_result: TestRunResult
    if request.run_tests == 1:
        test_result = run_local_checks(workdir=request.workdir, commands=request.test_commands)
    else:
        test_result = _empty_test_result()

    initial_pass_ok: int = _pass_is_acceptable(
        codex_result=codex_result,
        review_result=review_result,
        scope_evaluation=scope_evaluation,
        test_result=test_result,
    )

    final_codex_result: CodexRunResult = codex_result
    final_review_result: ReviewResult = review_result
    final_scope_evaluation: ScopeEvaluation = scope_evaluation
    final_test_result: TestRunResult = test_result
    repair_attempt: RepairAttemptResult = _empty_repair_attempt()
    repair_attempted: int = 0
    repair_ok: int = 0
    loop_status: str

    if initial_pass_ok == 1:
        loop_status = "initial_pass_success"
    elif repo_was_clean == 0:
        loop_status = "repair_skipped_due_to_dirty_repo"
    elif request.run_codex == 0:
        loop_status = "repair_skipped_due_to_codex_disabled"
    else:
        repair_attempted = 1
        failing_checks_summary: str = summarize_failed_checks(test_result)
        repair_prompt: str = build_repair_prompt(
            original_task=request.task,
            review_summary=review_result.summary,
            failing_checks_summary=failing_checks_summary,
        )
        repair_codex_result: CodexRunResult = run_codex_prompt(
            prompt=repair_prompt,
            workdir=request.workdir,
            command_template=request.codex_command or "codex",
            timeout_seconds=request.codex_timeout_seconds,
            prompt_via_stdin=request.codex_prompt_via_stdin,
        )
        repair_review_result: ReviewResult = review_changes(request.workdir, request.task)
        repair_scope_evaluation: ScopeEvaluation = _scope_evaluation_from_review(
            repair_review_result
        )
        repair_test_result: TestRunResult = (
            run_local_checks(workdir=request.workdir, commands=request.test_commands)
            if request.run_tests == 1
            else _empty_test_result()
        )
        repair_ok = _pass_is_acceptable(
            codex_result=repair_codex_result,
            review_result=repair_review_result,
            scope_evaluation=repair_scope_evaluation,
            test_result=repair_test_result,
        )
        repair_attempt = RepairAttemptResult(
            attempted=1,
            ok=repair_ok,
            prompt_summary=_trim_prompt_summary(repair_prompt),
            codex_result=repair_codex_result.model_dump(),
            review_result=repair_review_result.model_dump(),
            test_result=repair_test_result.model_dump(),
        )
        final_codex_result = repair_codex_result
        final_review_result = repair_review_result
        final_scope_evaluation = repair_scope_evaluation
        final_test_result = repair_test_result
        loop_status = "repair_success" if repair_ok == 1 else "repair_failed"

    final_pass_ok: int = _pass_is_acceptable(
        codex_result=final_codex_result,
        review_result=final_review_result,
        scope_evaluation=final_scope_evaluation,
        test_result=final_test_result,
    )

    git_action_result: GitActionResult = branch_result
    if final_pass_ok == 1 and final_scope_evaluation.ok == 1 and repo_was_clean == 1:
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

    loop_metadata: LoopMetadata = LoopMetadata(
        initial_pass_ok=initial_pass_ok,
        repair_attempted=repair_attempted,
        repair_ok=repair_ok,
        final_pass_ok=final_pass_ok,
        loop_status=loop_status if final_codex_result.ok == 1 else "hard_failure",
    )
    reviewer_narrative: ReviewerNarrative = build_reviewer_narrative(final_review_result)
    pr_metadata: PRMetadata = build_pr_metadata(
        task=request.task,
        review_result=final_review_result,
    )

    merge_recommendation: str = _final_merge_recommendation(
        branch_ok=branch_result.ok,
        final_codex_ok=final_codex_result.ok,
        final_review_ok=final_review_result.ok,
        final_tests_ok=final_test_result.all_passed,
        repair_attempted=repair_attempted,
    )
    success: int = 1 if merge_recommendation == "ready_for_pr" else 0

    return DevRunResult(
        task=request.task,
        workdir=request.workdir,
        started_at=started_at,
        finished_at=finished_at,
        plan=plan,
        codex=final_codex_result,
        tests=final_test_result,
        repair_attempt=repair_attempt.model_dump(),
        loop_metadata=loop_metadata.model_dump(),
        scope_evaluation=final_scope_evaluation.model_dump(),
        pr_metadata=pr_metadata.model_dump(),
        reviewer_narrative=reviewer_narrative.model_dump(),
        review_result=final_review_result.model_dump(),
        git_action_result=git_action_result.model_dump(),
        git=git_summary,
        branch_name=branch_result.branch_name,
        merge_recommendation=merge_recommendation,
        success=success,
    )
