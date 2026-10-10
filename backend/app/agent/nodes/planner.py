"""Planning and task decomposition node for the LangGraph autonomous agent.

Uses Gemma 2 to construct an evidence-driven, sequential execution plan
based on repository metadata, project manifests, and execution mode.
"""

import logging
from typing import Any, Dict, List

from app.agent.prompts import SYSTEM_PROMPT_AGENT_CORE, build_planner_prompt
from app.agent.schemas import PlanItem, PlanOutput, parse_and_validate_json
from app.agent.state import AgentState
from app.core.config import settings
from app.core.events import EventType, event_bus
from app.integrations.ollama_client import ollama_client

logger = logging.getLogger("outofoffice.agent.planner")


def _generate_fallback_plan(task_prompt: str, repo_meta: Dict[str, Any], mode: str) -> PlanOutput:
    """Provides a deterministic default plan if the LLM is unreachable or returns malformed JSON."""
    test_fw = repo_meta.get("test_framework", "pytest")
    test_cmd = repo_meta.get("test_command", "python -m pytest")

    steps: List[PlanItem] = [
        PlanItem(
            step_index=1,
            step_name="Repository Discovery & Manifest Scan",
            tool_name="repo_discovery",
            tool_args={},
            rationale="Index directory structure, source files, and dependencies",
        ),
        PlanItem(
            step_index=2,
            step_name=f"Run Baseline Test Suite ({test_fw})",
            tool_name="test_runner",
            tool_args={"command": test_cmd},
            rationale="Verify current test suite pass/fail baseline before investigation",
        ),
        PlanItem(
            step_index=3,
            step_name="AST Symbol Indexing & Dead Code Scan",
            tool_name="ast_parser",
            tool_args={},
            rationale="Extract exported functions and find unreferenced symbol candidates",
        ),
        PlanItem(
            step_index=4,
            step_name="Static Analysis & Linter Scan",
            tool_name="linter_runner",
            tool_args={},
            rationale="Check for syntax errors, type issues, and TODO/FIXME markers",
        ),
        PlanItem(
            step_index=5,
            step_name="Dependency & Manifest Audit",
            tool_name="dependency_auditor",
            tool_args={},
            rationale="Cross-reference declared packages against actual source code imports",
        ),
    ]

    if mode == "FIX":
        steps.append(
            PlanItem(
                step_index=6,
                step_name="Apply Surgical Fixes & Validate",
                tool_name="patcher",
                tool_args={},
                rationale="Apply isolated patches on agent branch and re-run test suite to verify",
            )
        )

    steps.append(
        PlanItem(
            step_index=len(steps) + 1,
            step_name="Synthesize Final Report & Voice Briefing",
            tool_name="reporter",
            tool_args={},
            rationale="Compute repository health score (0-100) and draft ElevenLabs audio brief",
        )
    )

    return PlanOutput(
        summary=f"Autonomous plan to analyze codebase for task: '{task_prompt[:60]}...'",
        estimated_minutes=5,
        steps=steps,
    )


async def planning_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node that generates the structured step-by-step execution plan."""
    job_id = state.get("job_id", "")
    task_prompt = state.get("task_prompt", "")
    repo_meta = state.get("repo_meta", {})
    mode = state.get("mode", "AUDIT")
    model_name = state.get("model_name") or settings.DEFAULT_MODEL

    logger.info(f"[{job_id}] Planning node started for task: '{task_prompt}' (Mode: {mode})")

    prompt = build_planner_prompt(
        task_prompt=task_prompt,
        repo_meta=repo_meta,
        mode=mode,
    )

    plan_output: PlanOutput

    try:
        if ollama_client.is_running():
            # Query local Gemma
            raw_response = await ollama_client.generate_async(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT_AGENT_CORE,
                model=model_name,
                format_json=True,
            )
            plan_output = parse_and_validate_json(raw_response, PlanOutput)
        else:
            logger.info(f"[{job_id}] Ollama offline; using deterministic fallback plan.")
            plan_output = _generate_fallback_plan(task_prompt, repo_meta, mode)

    except Exception as e:
        logger.warning(f"[{job_id}] Planning LLM query failed ({e}); activating fallback plan.")
        plan_output = _generate_fallback_plan(task_prompt, repo_meta, mode)

    plan_steps_dict = [s.model_dump() for s in plan_output.steps]

    # Emit event
    await event_bus.emit(
        EventType.STEP_COMPLETED,
        job_id=job_id,
        data={
            "step_name": "Agent Planning",
            "summary": plan_output.summary,
            "step_count": len(plan_steps_dict),
            "plan": plan_steps_dict,
        },
    )

    return {
        "plan_summary": plan_output.summary,
        "plan_steps": plan_steps_dict,
        "current_step_idx": 0,
        "logs": state.get("logs", []) + [f"Generated plan with {len(plan_steps_dict)} steps."],
    }
