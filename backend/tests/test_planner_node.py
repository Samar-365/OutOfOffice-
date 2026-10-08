"""Unit tests for the planning LangGraph node."""

import asyncio
from app.agent.nodes.planner import planning_node, _generate_fallback_plan
from app.agent.state import create_initial_agent_state


def test_planning_node_fallback_execution():
    state = create_initial_agent_state(
        job_id="test-plan-01",
        repo_path="/fake/repo",
        task_prompt="Find unused variables and clean tests",
        mode="FIX",
    )
    state["repo_meta"] = {
        "project_type": "FastAPI + React",
        "detected_languages": ["Python", "TypeScript"],
        "manifest_files": ["requirements.txt", "package.json"],
        "test_framework": "pytest",
        "file_count": 42,
    }

    result = asyncio.run(planning_node(state))
    assert "plan_steps" in result
    assert len(result["plan_steps"]) >= 5
    assert result["current_step_idx"] == 0
    assert any(s["tool_name"] == "repo_discovery" for s in result["plan_steps"])
    assert any(s["tool_name"] == "test_runner" for s in result["plan_steps"])
    assert any(s["tool_name"] == "patcher" for s in result["plan_steps"])


def test_generate_fallback_plan():
    repo_meta = {"test_framework": "vitest", "test_command": "npx vitest run"}
    plan = _generate_fallback_plan("Dead code cleanup", repo_meta, "AUDIT")
    assert len(plan.steps) == 6
    assert plan.steps[0].tool_name == "repo_discovery"
    # In AUDIT mode, patcher should not be included
    assert not any(s.tool_name == "patcher" for s in plan.steps)
