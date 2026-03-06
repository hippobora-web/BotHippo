"""Supervisor for local development task orchestration."""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone

from dev_orchestrator.codex_runner import build_repair_prompt, run_codex_prompt
from dev_orchestrator.github_pr import create_pull_request, merge_pull_request
from dev_orchestrator.git_runner import (
    collect_git_summary,
    commit_all_changes,
    create_task_branch,
    is_repo_clean,
    push_branch,
)
from dev_orchestrator.planner import build_codex_prompt, build_execution_plan
from dev_orchestrator.queue_runner import (
    build_request_from_queue_item,
    default_state_path,
    is_terminal_status,
    load_task_queue,
    load_or_initialize_queue_state,
    save_queue_state,
    summarize_queue_results,
    update_task_state,
)
from dev_orchestrator.reviewer import (
    build_pr_metadata,
    build_reviewer_narrative,
    is_dev_orchestrator_only_change,
    is_evengine_only_change,
    is_safe_evengine_change,
    review_changes,
)
from dev_orchestrator.schemas import (
    AutoLoopResult,
    CodexRunResult,
    DiscoveryResult,
    DevRunResult,
    DevTaskRequest,
    GitActionResult,
    LoopMetadata,
    PersistentQueueState,
    PRMetadata,
    RepairAttemptResult,
    ReviewResult,
    ReviewerNarrative,
    QueueRunResult,
    ScopeEvaluation,
    TestRunResult,
)
from dev_orchestrator.task_discovery import discover_tasks, write_discovery_queue
from dev_orchestrator.test_runner import run_local_checks, summarize_failed_checks


def _run_git(args: list[str], repo_path: str) -> subprocess.CompletedProcess[str]:
    """Run a git command for queue branch management without raising."""

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


def _current_branch_name(repo_path: str) -> str:
    """Return current branch name or empty string."""

    result: subprocess.CompletedProcess[str] = _run_git(
        ["rev-parse", "--abbrev-ref", "HEAD"],
        repo_path,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _switch_to_branch(repo_path: str, branch_name: str) -> int:
    """Switch to a branch and return 1 on success."""

    if not branch_name:
        return 0
    result: subprocess.CompletedProcess[str] = _run_git(["switch", branch_name], repo_path)
    return 1 if result.returncode == 0 else 0


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


def _failed_queue_result(
    *,
    task: str,
    workdir: str,
    queue_index: int,
    queue_total: int,
    error_message: str,
) -> DevRunResult:
    """Build a minimal failed result-like payload for queue continuation."""

    started_at: str = datetime.now(timezone.utc).isoformat()
    finished_at: str = datetime.now(timezone.utc).isoformat()
    review_result: ReviewResult = _default_review_result(error_message)
    scope_evaluation: ScopeEvaluation = ScopeEvaluation(
        ok=0,
        summary=error_message,
    )
    reviewer_narrative: ReviewerNarrative = build_reviewer_narrative(review_result)
    pr_metadata: PRMetadata = build_pr_metadata(
        task=task or "invalid queue task",
        review_result=review_result,
    )
    return DevRunResult(
        task=task,
        workdir=workdir,
        started_at=started_at,
        finished_at=finished_at,
        plan=build_execution_plan(task or "invalid queue task"),
        codex=_skipped_codex_result(),
        tests=_empty_test_result(),
        repair_attempt=_empty_repair_attempt().model_dump(),
        loop_metadata=_default_loop_metadata("hard_failure").model_dump(),
        scope_evaluation=scope_evaluation.model_dump(),
        pr_metadata=pr_metadata.model_dump(),
        reviewer_narrative=reviewer_narrative.model_dump(),
        review_result=review_result.model_dump(),
        git_action_result=GitActionResult(
            ok=0,
            branch_name="",
            stderr=error_message,
        ).model_dump(),
        git=collect_git_summary(workdir),
        branch_name="",
        pr_url="",
        queue_index=queue_index,
        queue_total=queue_total,
        merge_recommendation="failed",
        success=0,
    )


def _dirty_repo_queue_result(
    *,
    task: str,
    workdir: str,
    queue_index: int,
    queue_total: int,
) -> DevRunResult:
    """Build a failed queue result for tasks skipped after repository contamination."""

    return _failed_queue_result(
        task=task,
        workdir=workdir,
        queue_index=queue_index,
        queue_total=queue_total,
        error_message="queue_stopped_due_to_dirty_repo",
    )


def _queue_task_status_from_result(result: dict) -> str:
    """Map one task result dict to a persistent queue task status."""

    merge_recommendation: str = str(result.get("merge_recommendation", ""))
    if result.get("success") == 1 or merge_recommendation == "ready_for_pr":
        return "done"
    if merge_recommendation in {"failed", "failed_after_repair", "needs_review"}:
        return "failed"
    return "failed"


def _mark_remaining_tasks_skipped(
    *,
    queued_items: list,
    start_index: int,
    queue_total: int,
    workdir: str,
    state: PersistentQueueState,
    results: list[dict],
) -> PersistentQueueState:
    """Mark remaining queued tasks as skipped and append result-like entries."""

    updated_state: PersistentQueueState = state
    for remaining_index, remaining_item in enumerate(
        queued_items[start_index - 1 :],
        start=start_index,
    ):
        skipped_result: DevRunResult = _dirty_repo_queue_result(
            task=remaining_item.task,
            workdir=workdir,
            queue_index=remaining_index,
            queue_total=queue_total,
        )
        skipped_result_dict: dict = skipped_result.model_dump()
        results.append(skipped_result_dict)
        updated_state = update_task_state(
            state=updated_state,
            queue_index=remaining_index,
            status="skipped",
            result=skipped_result_dict,
        )
        save_queue_state(updated_state)
    return updated_state


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


def _append_git_action_error(
    git_action_result: GitActionResult,
    error_message: str,
) -> GitActionResult:
    """Append an additional safe error message to a git action result."""

    if not error_message:
        return git_action_result
    existing_stderr: str = git_action_result.stderr.strip()
    combined_stderr: str = error_message if not existing_stderr else f"{existing_stderr}\n{error_message}"
    return git_action_result.model_copy(update={"stderr": combined_stderr})


def _sync_main_after_merge(repo_path: str) -> tuple[int, str]:
    """Switch to main and pull latest changes after a successful auto-merge."""

    switch_result: subprocess.CompletedProcess[str] = _run_git(["switch", "main"], repo_path)
    if switch_result.returncode != 0:
        return 0, "post_merge_switch_main_failed"

    pull_result: subprocess.CompletedProcess[str] = _run_git(["pull", "origin", "main"], repo_path)
    if pull_result.returncode != 0:
        return 0, "post_merge_pull_main_failed"

    return 1, ""


def _auto_merge_allowed(
    *,
    merge_recommendation: str,
    git_action_result: GitActionResult,
    pr_url: str,
    review_result: ReviewResult,
    scope_evaluation: ScopeEvaluation,
    tests_passed: int,
    repo_was_clean: int,
) -> int:
    """Return 1 only when all strict auto-merge prerequisites are satisfied."""

    if merge_recommendation != "ready_for_pr":
        return 0
    if git_action_result.ok != 1:
        return 0
    if not pr_url.strip():
        return 0
    if review_result.ok != 1:
        return 0
    if scope_evaluation.ok != 1:
        return 0
    if tests_passed != 1:
        return 0
    if repo_was_clean != 1:
        return 0
    return 1


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
            pr_url="",
            auto_merge_attempted=0,
            auto_merge_ok=0,
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
    pr_url: str = ""
    if merge_recommendation == "ready_for_pr" and git_action_result.ok == 1:
        pr_created_ok, pr_url = create_pull_request(
            repo_path=request.workdir,
            branch_name=branch_result.branch_name,
            title=pr_metadata.suggested_title,
            body=pr_metadata.suggested_description,
        )
        if pr_created_ok == 0:
            pr_url = ""
    auto_merge_attempted: int = 0
    auto_merge_ok: int = 0
    if _auto_merge_allowed(
        merge_recommendation=merge_recommendation,
        git_action_result=git_action_result,
        pr_url=pr_url,
        review_result=final_review_result,
        scope_evaluation=final_scope_evaluation,
        tests_passed=final_test_result.all_passed,
        repo_was_clean=repo_was_clean,
    ) == 1:
        dev_only: int = is_dev_orchestrator_only_change(final_review_result)
        evengine_only: int = is_evengine_only_change(final_review_result)
        if dev_only == 1 or (evengine_only == 1 and is_safe_evengine_change(final_review_result) == 1):
            auto_merge_attempted = 1
            auto_merge_ok = merge_pull_request(
                repo_path=request.workdir,
                pr_url=pr_url,
            )
            if auto_merge_ok == 1:
                main_sync_ok, main_sync_error = _sync_main_after_merge(request.workdir)
                if main_sync_ok == 0:
                    git_action_result = _append_git_action_error(git_action_result, main_sync_error)
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
        pr_url=pr_url,
        auto_merge_attempted=auto_merge_attempted,
        auto_merge_ok=auto_merge_ok,
        merge_recommendation=merge_recommendation,
        success=success,
    )


def run_development_queue(
    *,
    queue_path: str,
    default_workdir: str,
    default_run_codex: int,
    default_run_tests: int,
    default_codex_command: str | None,
    default_codex_timeout_seconds: int,
    default_codex_prompt_via_stdin: int,
    resume: int = 0,
    state_path: str | None = None,
) -> QueueRunResult:
    """Run a task queue sequentially and return structured queue results."""

    queued_items = load_task_queue(queue_path)
    queue_total: int = len(queued_items)
    effective_state_path: str = state_path or default_state_path(queue_path)
    persistent_state: PersistentQueueState = load_or_initialize_queue_state(
        queue_path=queue_path,
        state_path=effective_state_path,
        queued_items=queued_items,
        resume=resume,
    )
    started_at: str = persistent_state.started_at
    base_branch: str = _current_branch_name(default_workdir)
    results: list[dict] = []

    for queue_index, item in enumerate(queued_items, start=1):
        persisted_task = persistent_state.tasks[queue_index - 1]
        if resume == 1 and is_terminal_status(persisted_task.status):
            if persisted_task.result:
                results.append(persisted_task.result)
            else:
                resumed_failed_result: DevRunResult = _failed_queue_result(
                    task=item.task,
                    workdir=default_workdir,
                    queue_index=queue_index,
                    queue_total=queue_total,
                    error_message="queue_state_missing_result",
                )
                resumed_failed_result_dict: dict = resumed_failed_result.model_dump()
                results.append(resumed_failed_result_dict)
                persistent_state = update_task_state(
                    state=persistent_state,
                    queue_index=queue_index,
                    status="failed",
                    result=resumed_failed_result_dict,
                )
                save_queue_state(persistent_state)
            continue

        repo_is_clean: int = is_repo_clean(default_workdir)
        if repo_is_clean == 1 and base_branch:
            _switch_to_branch(default_workdir, base_branch)
            if _current_branch_name(default_workdir) != base_branch:
                failed_result: DevRunResult = _failed_queue_result(
                    task=item.task,
                    workdir=default_workdir,
                    queue_index=queue_index,
                    queue_total=queue_total,
                    error_message="queue_stopped_due_to_branch_restore_failure",
                )
                failed_result_dict: dict = failed_result.model_dump()
                results.append(failed_result_dict)
                persistent_state = update_task_state(
                    state=persistent_state,
                    queue_index=queue_index,
                    status="failed",
                    result=failed_result_dict,
                )
                save_queue_state(persistent_state)
                for remaining_index, remaining_item in enumerate(
                    queued_items[queue_index:],
                    start=queue_index + 1,
                ):
                    remaining_failed_result: DevRunResult = _failed_queue_result(
                        task=remaining_item.task,
                        workdir=default_workdir,
                        queue_index=remaining_index,
                        queue_total=queue_total,
                        error_message="queue_stopped_due_to_branch_restore_failure",
                    )
                    remaining_failed_result_dict: dict = remaining_failed_result.model_dump()
                    results.append(remaining_failed_result_dict)
                    persistent_state = update_task_state(
                        state=persistent_state,
                        queue_index=remaining_index,
                        status="failed",
                        result=remaining_failed_result_dict,
                    )
                    save_queue_state(persistent_state)
                break
        elif repo_is_clean == 0:
            persistent_state = _mark_remaining_tasks_skipped(
                queued_items=queued_items,
                start_index=queue_index,
                queue_total=queue_total,
                workdir=default_workdir,
                state=persistent_state,
                results=results,
            )
            break

        try:
            request: DevTaskRequest = build_request_from_queue_item(
                item=item,
                default_workdir=default_workdir,
                default_run_codex=default_run_codex,
                default_run_tests=default_run_tests,
                default_codex_command=default_codex_command,
                default_codex_timeout_seconds=default_codex_timeout_seconds,
                default_codex_prompt_via_stdin=default_codex_prompt_via_stdin,
            )
        except ValueError as exc:
            failed_result: DevRunResult = _failed_queue_result(
                task=item.task,
                workdir=default_workdir,
                queue_index=queue_index,
                queue_total=queue_total,
                error_message=str(exc),
            )
            failed_result_dict: dict = failed_result.model_dump()
            results.append(failed_result_dict)
            persistent_state = update_task_state(
                state=persistent_state,
                queue_index=queue_index,
                status="failed",
                result=failed_result_dict,
            )
            save_queue_state(persistent_state)
            continue

        persistent_state = update_task_state(
            state=persistent_state,
            queue_index=queue_index,
            status="running",
        )
        save_queue_state(persistent_state)

        try:
            result: DevRunResult = run_development_task(request).model_copy(
                update={
                    "queue_index": queue_index,
                    "queue_total": queue_total,
                }
            )
        except Exception as exc:
            result = _failed_queue_result(
                task=item.task,
                workdir=default_workdir,
                queue_index=queue_index,
                queue_total=queue_total,
                error_message=f"queue_task_execution_failed:{exc.__class__.__name__}",
            )

        result_dict: dict = result.model_dump()
        results.append(result_dict)
        persistent_state = update_task_state(
            state=persistent_state,
            queue_index=queue_index,
            status=_queue_task_status_from_result(result_dict),
            result=result_dict,
        )
        save_queue_state(persistent_state)

        if is_repo_clean(default_workdir) == 0:
            persistent_state = _mark_remaining_tasks_skipped(
                queued_items=queued_items,
                start_index=queue_index + 1,
                queue_total=queue_total,
                workdir=default_workdir,
                state=persistent_state,
                results=results,
            )
            break

        if base_branch and is_repo_clean(default_workdir) == 1:
            _switch_to_branch(default_workdir, base_branch)

    save_queue_state(persistent_state)
    reloaded_state: PersistentQueueState = load_or_initialize_queue_state(
        queue_path=queue_path,
        state_path=effective_state_path,
        queued_items=queued_items,
        resume=1,
    )
    finished_at: str = reloaded_state.finished_at or datetime.now(timezone.utc).isoformat()
    summary = summarize_queue_results(results)
    return QueueRunResult(
        queue_path=queue_path,
        state_path=effective_state_path,
        resumed=resume,
        started_at=started_at,
        finished_at=finished_at,
        results=results,
        summary=summary.model_dump(),
    )


def run_task_discovery(
    *,
    repo_path: str,
    output_queue_path: str | None = None,
) -> DiscoveryResult:
    """Run deterministic repository task discovery and optionally write a queue file."""

    discovery_result: DiscoveryResult = discover_tasks(repo_path)
    if output_queue_path:
        written_queue_path: str = write_discovery_queue(
            discovery_result=discovery_result,
            queue_path=output_queue_path,
        )
        discovery_result = discovery_result.model_copy(
            update={"output_queue_path": written_queue_path}
        )
    return discovery_result


def run_autonomous_development_loop(
    *,
    workdir: str,
    max_cycles: int,
    max_tasks_per_cycle: int,
    queue_dir: str,
    run_codex: int,
    run_tests: int,
    codex_command: str | None,
    codex_timeout_seconds: int,
    codex_prompt_via_stdin: int,
) -> AutoLoopResult:
    """Run the bounded autonomous discovery and queue execution loop."""

    from dev_orchestrator.autoloop import run_autonomous_loop

    return run_autonomous_loop(
        workdir=workdir,
        max_cycles=max_cycles,
        max_tasks_per_cycle=max_tasks_per_cycle,
        queue_dir=queue_dir,
        run_codex=run_codex,
        run_tests=run_tests,
        codex_command=codex_command,
        codex_timeout_seconds=codex_timeout_seconds,
        codex_prompt_via_stdin=codex_prompt_via_stdin,
    )
