"""Supervisor for local development task orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

from dev_orchestrator.codex_runner import run_codex_prompt
from dev_orchestrator.git_runner import collect_git_summary
from dev_orchestrator.planner import build_codex_prompt, build_execution_plan
from dev_orchestrator.schemas import CodexRunResult, DevRunResult, DevTaskRequest, TestRunResult
from dev_orchestrator.test_runner import run_local_checks


def run_development_task(request: DevTaskRequest) -> DevRunResult:
    """Run the end-to-end local development orchestrator workflow."""

    started_at: str = datetime.now(timezone.utc).isoformat()
    plan = build_execution_plan(request.task)
    codex_prompt: str = build_codex_prompt(request.task, plan)

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
        codex_result = CodexRunResult(
            attempted=0,
            success=1,
            error_message="codex_skipped",
        )

    test_result: TestRunResult
    if request.run_tests == 1:
        test_result = run_local_checks(workdir=request.workdir, commands=request.test_commands)
    else:
        test_result = TestRunResult(
            attempted=0,
            all_passed=1,
            checks=[],
        )

    git_summary = collect_git_summary(request.workdir)
    finished_at: str = datetime.now(timezone.utc).isoformat()

    overall_success: int = 1 if codex_result.success == 1 and test_result.all_passed == 1 else 0
    return DevRunResult(
        task=request.task,
        workdir=request.workdir,
        started_at=started_at,
        finished_at=finished_at,
        plan=plan,
        codex=codex_result,
        tests=test_result,
        git=git_summary,
        success=overall_success,
    )

