"""Tool execution and feedback node for the LangGraph agent workflow.

Routes planned steps to deterministic tools (repo discovery, AST indexing,
test suite runner, static analysis, dependency auditor, and ripgrep searcher),
captures execution latency, and broadcasts real-time telemetry events.
"""

import logging
import time
from typing import Any, Dict, List

from app.agent.state import AgentState
from app.core.events import EventType, event_bus
from app.tools.ast_parser import build_symbol_table
from app.tools.dependency_auditor import audit_dependencies
from app.tools.linter_runner import run_static_analysis
from app.tools.repo_discovery import discover_repository
from app.tools.search_engine import find_dead_code_candidates, search_code
from app.tools.test_runner import run_test_suite

logger = logging.getLogger("outofoffice.agent.executor")


async def executor_node(state: AgentState) -> Dict[str, Any]:
    """Executes the current step in the agent's planned sequence."""
    job_id = state.get("job_id", "")
    repo_path = state.get("repo_path", "")
    plan_steps = state.get("plan_steps", [])
    current_idx = state.get("current_step_idx", 0)

    if current_idx >= len(plan_steps):
        logger.info(f"[{job_id}] All {len(plan_steps)} plan steps completed.")
        return {"current_step_idx": current_idx}

    step = plan_steps[current_idx]
    tool_name = step.get("tool_name", "")
    step_name = step.get("step_name", f"Step {current_idx + 1}")
    tool_args = step.get("tool_args", {})

    logger.info(f"[{job_id}] Executing Step {current_idx + 1}/{len(plan_steps)}: '{step_name}' via tool '{tool_name}'")

    # Emit step started event
    await event_bus.emit(
        EventType.STEP_STARTED,
        job_id=job_id,
        data={
            "step_index": current_idx + 1,
            "step_name": step_name,
            "tool_name": tool_name,
        },
    )

    start_time = time.time()
    tool_output: Dict[str, Any] = {}
    stdout_summary = ""
    stderr_summary = ""
    step_status = "SUCCESS"

    # State update accumulator
    updates: Dict[str, Any] = {
        "current_step_idx": current_idx + 1,
    }

    try:
        if tool_name == "repo_discovery":
            tool_output = discover_repository(repo_path)
            updates["repo_meta"] = tool_output
            stdout_summary = f"Indexed {tool_output.get('file_count', 0)} files. Project: {tool_output.get('project_type')}"

        elif tool_name == "test_runner":
            cmd = tool_args.get("command")
            res = run_test_suite(repo_path, custom_command=cmd)
            tool_output = res.to_dict()
            updates["test_results"] = tool_output
            stdout_summary = f"Tests: {res.passed} passed, {res.failed} failed, {res.skipped} skipped"
            stderr_summary = getattr(res, "stderr_snippet", res.stderr)

        elif tool_name == "ast_parser":
            table = build_symbol_table(repo_path)
            dead_code = find_dead_code_candidates(repo_path, max_check=25)
            tool_output = {
                "total_symbols": table.get("total_symbols", 0),
                "dead_code_candidates": dead_code,
            }
            updates["dead_code_candidates"] = dead_code
            stdout_summary = f"Extracted {table.get('total_symbols', 0)} symbols. Found {len(dead_code)} dead code candidates."

        elif tool_name == "linter_runner":
            static_res = run_static_analysis(repo_path)
            tool_output = static_res
            updates["static_issues"] = static_res.get("issues", [])
            stdout_summary = f"Static analysis: {static_res.get('total_issues', 0)} issues ({static_res.get('high_severity', 0)} high, {static_res.get('medium_severity', 0)} medium)"

        elif tool_name == "dependency_auditor":
            dep_res = audit_dependencies(repo_path)
            tool_output = dep_res
            updates["dependency_issues"] = dep_res
            stdout_summary = f"Dependency audit: {dep_res.get('total_unused_count', 0)} unused declared packages"

        elif tool_name == "search_engine":
            pattern = tool_args.get("pattern", "")
            matches = search_code(repo_path, pattern=pattern)
            tool_output = {"matches_count": len(matches), "matches": matches[:10]}
            stdout_summary = f"Ripgrep search for '{pattern}': {len(matches)} matches found"

        else:
            # Generic step / pass-through
            stdout_summary = f"Executed {step_name}"

    except Exception as e:
        logger.error(f"[{job_id}] Tool {tool_name} failed: {e}")
        step_status = "FAILED"
        stderr_summary = str(e)
        updates["errors"] = state.get("errors", []) + [f"Step {step_name} failed: {e}"]

    duration_ms = round((time.time() - start_time) * 1000, 2)

    # Append to tool history
    history_entry = {
        "step_index": current_idx + 1,
        "step_name": step_name,
        "tool_name": tool_name,
        "status": step_status,
        "duration_ms": duration_ms,
        "stdout": stdout_summary,
        "stderr": stderr_summary,
    }
    updates["tool_history"] = state.get("tool_history", []) + [history_entry]

    # Emit step completed event
    await event_bus.emit(
        EventType.STEP_COMPLETED,
        job_id=job_id,
        data=history_entry,
    )

    return updates
