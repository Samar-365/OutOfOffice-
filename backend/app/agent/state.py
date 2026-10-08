"""Agent state and context schema definition for LangGraph workflow execution.

Tracks repository metadata, planned steps, tool execution traces, findings,
diffs, test metrics, and health scores across graph nodes.
"""

import time
from typing import Any, Dict, List, Optional, TypedDict


class AgentState(TypedDict, total=False):
    """Unified state dictionary passed between all nodes in the agent execution graph."""

    # Job Core Identity
    job_id: str
    repo_path: str
    task_prompt: str
    mode: str  # AUDIT or FIX
    model_name: str
    status: str  # QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED

    # Git & Repository Metadata
    repo_meta: Dict[str, Any]
    base_branch: Optional[str]
    agent_branch: Optional[str]

    # Autonomous Planning & Step Navigation
    plan_summary: str
    plan_steps: List[Dict[str, Any]]
    current_step_idx: int
    tool_history: List[Dict[str, Any]]

    # Findings & Diagnostic Ledger
    findings: List[Dict[str, Any]]
    dead_code_candidates: List[Dict[str, Any]]
    static_issues: List[Dict[str, Any]]
    dependency_issues: List[Dict[str, Any]]

    # Fixes & Unified Diffs (Fix Mode)
    diffs: List[Dict[str, Any]]
    test_results: Optional[Dict[str, Any]]
    post_fix_test_results: Optional[Dict[str, Any]]

    # Diagnostic Logs & Error Handling
    errors: List[str]
    logs: List[str]

    # Final Synthesis & Telemetry
    health_score: Optional[int]
    final_report_markdown: Optional[str]
    voice_brief_script: Optional[str]
    audio_path: Optional[str]

    # "Touch Grass" Timing Tracking
    away_start_timestamp: float
    away_duration_minutes: float


def create_initial_agent_state(
    job_id: str,
    repo_path: str,
    task_prompt: str,
    mode: str = "AUDIT",
    model_name: Optional[str] = None,
) -> AgentState:
    """Instantiates a fresh AgentState with defaults."""
    return AgentState(
        job_id=job_id,
        repo_path=repo_path,
        task_prompt=task_prompt,
        mode=mode.upper(),
        model_name=model_name or "gemma2:9b",
        status="RUNNING",
        repo_meta={},
        base_branch=None,
        agent_branch=None,
        plan_summary="",
        plan_steps=[],
        current_step_idx=0,
        tool_history=[],
        findings=[],
        dead_code_candidates=[],
        static_issues=[],
        dependency_issues=[],
        diffs=[],
        test_results=None,
        post_fix_test_results=None,
        errors=[],
        logs=[],
        health_score=None,
        final_report_markdown=None,
        voice_brief_script=None,
        audio_path=None,
        away_start_timestamp=time.time(),
        away_duration_minutes=0.0,
    )
