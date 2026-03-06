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


class DiscoveredTask(BaseModel):
    """One deterministic candidate development task discovered from the repository."""

    task: str
    priority: int
    source: str
    evidence: list[str] = Field(default_factory=list)


class DiscoveryResult(BaseModel):
    """Structured result of deterministic repository task discovery."""

    repo_path: str
    started_at: str
    finished_at: str
    tasks: list[DiscoveredTask] = Field(default_factory=list)
    output_queue_path: str = ""


class AutoLoopCycleResult(BaseModel):
    """Structured result for one bounded autonomous loop cycle."""

    cycle_index: int
    discovered_task_count: int
    queue_path: str = ""
    queue_result: dict = Field(default_factory=dict)
    stopped_reason: str = ""


class AutoLoopResult(BaseModel):
    """Structured result for a bounded autonomous development loop."""

    workdir: str
    started_at: str
    finished_at: str
    max_cycles: int
    completed_cycles: int
    cycles: list[AutoLoopCycleResult] = Field(default_factory=list)
    stopped_reason: str = ""


class QueuedTaskItem(BaseModel):
    """One queued development task with optional per-item overrides."""

    task: str
    run_codex: Optional[int] = None
    run_tests: Optional[int] = None
    codex_command: Optional[str] = None
    codex_timeout_seconds: Optional[int] = None
    codex_prompt_via_stdin: Optional[int] = None
    test_commands: list[str] = Field(default_factory=list)


class QueueRunSummary(BaseModel):
    """Aggregate counts for a queued orchestrator execution."""

    total_tasks: int
    succeeded: int
    failed: int
    needs_review: int
    failed_after_repair: int
    ready_for_pr: int


class QueueRunResult(BaseModel):
    """Structured result for a sequential queue execution."""

    queue_path: str
    state_path: str = ""
    resumed: int = 0
    started_at: str
    finished_at: str
    results: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class PersistentQueueTaskState(BaseModel):
    """Persistent per-task execution state for a queue run."""

    task: str
    status: str
    queue_index: int
    result: dict = Field(default_factory=dict)


class PersistentQueueState(BaseModel):
    """Persistent queue execution state stored on disk."""

    queue_path: str
    state_path: str
    started_at: str
    updated_at: str
    finished_at: str = ""
    tasks: list[PersistentQueueTaskState] = Field(default_factory=list)


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
    pr_url: str = ""
    auto_merge_attempted: int = 0
    auto_merge_ok: int = 0
    queue_index: Optional[int] = None
    queue_total: Optional[int] = None
    merge_recommendation: str
    success: int
