"""Task planning utilities for the local development orchestrator."""

from __future__ import annotations

from dev_orchestrator.schemas import ExecutionPlan, PlanStep


def build_execution_plan(task: str) -> ExecutionPlan:
    """Build a deterministic, structured execution plan from a task string."""

    task_lower: str = task.lower()
    plan_steps: list[PlanStep] = [
        PlanStep(
            step_id="1",
            title="Analyze Task",
            description="Read the request and identify target files and constraints.",
        ),
        PlanStep(
            step_id="2",
            title="Implement Changes",
            description="Apply code changes in the repository according to the task.",
        ),
    ]

    if "test" in task_lower or "check" in task_lower or "validate" in task_lower:
        plan_steps.append(
            PlanStep(
                step_id="3",
                title="Run Verification",
                description="Execute local checks/tests and gather outputs.",
            )
        )
    else:
        plan_steps.append(
            PlanStep(
                step_id="3",
                title="Run Baseline Checks",
                description="Run baseline compile/test checks for regression safety.",
            )
        )

    plan_steps.extend(
        [
            PlanStep(
                step_id="4",
                title="Summarize Git Changes",
                description="Collect git status and diff summary of modifications.",
            ),
            PlanStep(
                step_id="5",
                title="Return Structured Result",
                description="Return a structured run result with plan, checks, and git summary.",
            ),
        ]
    )

    return ExecutionPlan(
        summary="Execute task with Codex wrapper, local checks, and git summary.",
        steps=plan_steps,
    )


def build_codex_prompt(task: str, plan: ExecutionPlan) -> str:
    """Compose a deterministic Codex prompt from task and plan."""

    step_lines: list[str] = [
        f"{step.step_id}. {step.title}: {step.description}" for step in plan.steps
    ]
    joined_steps: str = "\n".join(step_lines)
    return (
        "You are Codex operating in a local repository.\n"
        "Execute the following development task safely and deterministically.\n\n"
        f"Task:\n{task}\n\n"
        f"Execution Plan:\n{joined_steps}\n\n"
        "Constraints:\n"
        "- Keep changes minimal-risk and modular.\n"
        "- Run relevant local checks.\n"
        "- Summarize git status/diff at the end.\n"
        "- Do not auto-push or auto-merge.\n"
    )

