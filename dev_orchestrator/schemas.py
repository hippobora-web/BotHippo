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
    git: GitSummary
    success: int
