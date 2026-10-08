"""Autonomous Agent module for OutOfOffice AI."""
from .schemas import (
    PlanItem,
    PlanOutput,
    InvestigationOutput,
    PatchOutput,
    ReportOutput,
    extract_json_block,
    repair_json_string,
    parse_and_validate_json,
)
from .prompts import (
    SYSTEM_PROMPT_AGENT_CORE,
    build_planner_prompt,
    build_investigation_prompt,
    build_fixer_prompt,
    build_reporter_prompt,
)
from .state import AgentState, create_initial_agent_state

__all__ = [
    "PlanItem",
    "PlanOutput",
    "InvestigationOutput",
    "PatchOutput",
    "ReportOutput",
    "extract_json_block",
    "repair_json_string",
    "parse_and_validate_json",
    "SYSTEM_PROMPT_AGENT_CORE",
    "build_planner_prompt",
    "build_investigation_prompt",
    "build_fixer_prompt",
    "build_reporter_prompt",
    "AgentState",
    "create_initial_agent_state",
]
