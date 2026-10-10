"""LangGraph workflow assembly, conditional transitions, and execution graph engine.

Orchestrates the complete cyclic reasoning loop:
START -> Discovery/Planning -> Executor Loop -> Investigator -> Fixer (if FIX mode) -> Reporter -> END
"""

import asyncio
import logging
from typing import Any, Callable, Dict, Optional

from app.agent.nodes.executor import executor_node
from app.agent.nodes.fixer import fixer_node
from app.agent.nodes.investigator import investigator_node
from app.agent.nodes.planner import planning_node
from app.agent.nodes.reporter import reporter_node
from app.agent.state import AgentState, create_initial_agent_state
from app.core.events import EventType, event_bus
from app.integrations.sentry_telemetry import sentry_tracer
from app.tools.repo_discovery import discover_repository

logger = logging.getLogger("outofoffice.agent.graph")


class AgentWorkflow:
    """Cyclic autonomous agent workflow graph."""

    def __init__(self):
        pass

    async def execute(
        self,
        job_id: str,
        repo_path: str,
        task_prompt: str,
        mode: str = "AUDIT",
        model_name: Optional[str] = None,
        on_step_update: Optional[Callable[[AgentState, str], Any]] = None,
    ) -> AgentState:
        """Executes the full agent graph sequentially with conditional transitions."""
        logger.info(f"[{job_id}] Initializing AgentWorkflow for '{repo_path}' in {mode} mode.")

        # Initialize State
        state = create_initial_agent_state(
            job_id=job_id,
            repo_path=repo_path,
            task_prompt=task_prompt,
            mode=mode,
            model_name=model_name,
        )

        # Notify Start
        await event_bus.emit(
            EventType.JOB_STARTED,
            job_id=job_id,
            data={
                "job_id": job_id,
                "repo_path": repo_path,
                "mode": mode,
                "task_prompt": task_prompt,
            },
        )

        async with sentry_tracer.trace_agent_job(job_id=job_id, repo_path=repo_path, mode=mode, model_name=model_name):
            # -------------------------------------------------------------
            # Node 0: Initial Repository Intake Discovery
            # -------------------------------------------------------------
            async with sentry_tracer.trace_step(job_id=job_id, step_name="Discovery", step_index=0):
                try:
                    repo_meta = discover_repository(repo_path)
                    state["repo_meta"] = repo_meta
                    if on_step_update:
                        await self._invoke_callback(on_step_update, state, "Discovery")
                except Exception as e:
                    logger.error(f"[{job_id}] Discovery failed: {e}")
                    state["errors"].append(f"Discovery error: {e}")

            # -------------------------------------------------------------
            # Node 1: Planning Node
            # -------------------------------------------------------------
            async with sentry_tracer.trace_step(job_id=job_id, step_name="Planning", step_index=1):
                try:
                    plan_updates = await planning_node(state)
                    state.update(plan_updates)
                    if on_step_update:
                        await self._invoke_callback(on_step_update, state, "Planning")
                except Exception as e:
                    logger.error(f"[{job_id}] Planning failed: {e}")
                    state["errors"].append(f"Planning error: {e}")

            # -------------------------------------------------------------
            # Node 2: Executor Loop (Iterates through planned tool steps)
            # -------------------------------------------------------------
            total_steps = len(state.get("plan_steps", []))
            while state.get("current_step_idx", 0) < total_steps:
                step_idx = state.get("current_step_idx", 0)
                step_obj = state.get("plan_steps", [])[step_idx] if step_idx < len(state.get("plan_steps", [])) else {}
                step_name_str = step_obj.get("step_name") or step_obj.get("description") or step_obj.get("tool_name") or f"Step {step_idx}"
                async with sentry_tracer.trace_step(job_id=job_id, step_name=step_name_str, step_index=2 + step_idx):
                    try:
                        exec_updates = await executor_node(state)
                        state.update(exec_updates)
                        if on_step_update:
                            await self._invoke_callback(on_step_update, state, step_name_str)
                    except Exception as e:
                        logger.error(f"[{job_id}] Step execution error: {e}")
                        state["errors"].append(f"Execution error: {e}")
                        state["current_step_idx"] = state.get("current_step_idx", 0) + 1

            # -------------------------------------------------------------
            # Node 3: Investigator Node (Root cause diagnosis & confidence)
            # -------------------------------------------------------------
            async with sentry_tracer.trace_step(job_id=job_id, step_name="Investigation", step_index=10):
                try:
                    inv_updates = await investigator_node(state)
                    state.update(inv_updates)
                    if on_step_update:
                        await self._invoke_callback(on_step_update, state, "Investigation")
                except Exception as e:
                    logger.error(f"[{job_id}] Investigation failed: {e}")
                    state["errors"].append(f"Investigation error: {e}")

            # -------------------------------------------------------------
            # Node 4: Fixer Node (Fix Mode only: applies & validates patches)
            # -------------------------------------------------------------
            if mode == "FIX":
                async with sentry_tracer.trace_step(job_id=job_id, step_name="Fixer", step_index=11):
                    try:
                        fix_updates = await fixer_node(state)
                        state.update(fix_updates)
                        if on_step_update:
                            await self._invoke_callback(on_step_update, state, "Fixer")
                    except Exception as e:
                        logger.error(f"[{job_id}] Fixer failed: {e}")
                        state["errors"].append(f"Fixer error: {e}")

            # -------------------------------------------------------------
            # Node 5: Reporter Node (Health Score & Voice Briefing)
            # -------------------------------------------------------------
            async with sentry_tracer.trace_step(job_id=job_id, step_name="Reporting", step_index=12):
                try:
                    rep_updates = await reporter_node(state)
                    state.update(rep_updates)
                    if on_step_update:
                        await self._invoke_callback(on_step_update, state, "Reporting")
                except Exception as e:
                    logger.error(f"[{job_id}] Reporting failed: {e}")
                    state["errors"].append(f"Reporting error: {e}")

        state["status"] = "COMPLETED" if not state.get("errors") else "COMPLETED_WITH_WARNINGS"
        logger.info(f"[{job_id}] Workflow execution complete. Health Score: {state.get('health_score')}/100.")
        return state

    async def _invoke_callback(
        self,
        callback: Callable[[AgentState, str], Any],
        state: AgentState,
        step_name: str,
    ):
        """Helper to invoke sync or async callbacks."""
        if asyncio.iscoroutinefunction(callback):
            await callback(state, step_name)
        else:
            callback(state, step_name)


# Global singleton workflow instance
agent_workflow = AgentWorkflow()
