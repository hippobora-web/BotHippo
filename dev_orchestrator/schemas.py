"""Schemas for the local development orchestrator."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class PlanStep(BaseModel):
    """One deterministic execution step in the orchestrator plan."""

    step_id: str
    title: str
    description: str
    status: str = "pending"


class ExecutionPlan(BaseModel):
    """Structured execution plan for a development task."""

    summary: str
    steps: list[PlanStep] = Field(default_factory=list)


class CodexRunResult(BaseModel):
    """Outcome of the Codex subprocess execution."""

    attempted: int
    ok: int
    success: int
    command: list[str] = Field(default_factory=list)
    return_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    error_message: str = ""
    duration_seconds: float = 0.0


class TestCheckResult(BaseModel):
    """Outcome of a single local test/check command."""

    name: str
    command: str
    return_code: int
    success: int
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0


class TestRunResult(BaseModel):
    """Aggregated test/check execution results."""

    attempted: int
    all_passed: int
    checks: list[TestCheckResult] = Field(default_factory=list)


class RepairAttemptResult(BaseModel):
    """Structured result of a single constrained repair attempt."""

    attempted: int
    ok: int
    prompt_summary: str = ""
    codex_result: dict = Field(default_factory=dict)
    review_result: dict = Field(default_factory=dict)
    test_result: dict = Field(default_factory=dict)


class LoopMetadata(BaseModel):
    """Metadata describing the self-repair loop outcome."""

    initial_pass_ok: int
    repair_attempted: int
    repair_ok: int
    final_pass_ok: int
    loop_status: str


class ScopeRule(BaseModel):
    """Deterministic scope rule for a task."""

    label: str
    allowed_prefixes: list[str] = Field(default_factory=list)
    blocked_prefixes: list[str] = Field(default_factory=list)


class ScopeEvaluation(BaseModel):
    """Evaluation of changed files against a task scope rule."""

    ok: int
    allowed_files: list[str] = Field(default_factory=list)
    out_of_scope_files: list[str] = Field(default_factory=list)
    blocked_files: list[str] = Field(default_factory=list)
    summary: str = ""


class ReviewerNarrative(BaseModel):
    """Human-readable deterministic reviewer summary."""

    summary: str = ""
    notable_changes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PRMetadata(BaseModel):
    """Suggested PR metadata derived deterministically from task and review."""

    suggested_title: str = ""
    suggested_description: str = ""
    change_scope_summary: str = ""
    risk_summary: str = ""


class ReviewResult(BaseModel):
    """Deterministic review result based on git changes."""

    ok: int
    summary: str
    changed_files: list[str] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    allowed_files: list[str] = Field(default_factory=list)
    out_of_scope_files: list[str] = Field(default_factory=list)
    blocked_files: list[str] = Field(default_factory=list)


class GitActionResult(BaseModel):
    """Result of a git action such as branch, commit, or push."""

    ok: int
    branch_name: str
    commit_sha: str = ""
    stdout: str = ""
    stderr: str = ""


class GitSummary(BaseModel):
    """Compact git status/diff summary after the run."""

    is_git_repo: int
    branch: str = ""
    status_short: str = ""
    diff_stat: str = ""
    staged_diff_stat: str = ""
    changed_files: list[str] = Field(default_factory=list)


class DevTaskRequest(BaseModel):
    """Input payload for a local orchestrator run."""

    task: str
    workdir: str = "."
    run_codex: int = 1
    run_tests: int = 1
    codex_command: Optional[str] = None
    codex_timeout_seconds: int = 1800
    codex_prompt_via_stdin: int = 1
    test_commands: list[str] = Field(default_factory=list)


class DevRunResult(BaseModel):
    """Final structured result of an orchestrated development run."""

    task: str
    workdir: str
    started_at: str
    finished_at: str
    plan: ExecutionPlan
    codex: CodexRunResult
    tests: TestRunResult
    repair_attempt: dict
    loop_metadata: dict
    scope_evaluation: dict = Field(default_factory=dict)
    pr_metadata: dict = Field(default_factory=dict)
    reviewer_narrative: dict = Field(default_factory=dict)
    review_result: dict
    git_action_result: dict
    git: GitSummary
    branch_name: str
    merge_recommendation: str
    success: int
