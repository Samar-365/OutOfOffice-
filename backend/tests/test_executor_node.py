"""Unit tests for the executor LangGraph node."""

import asyncio
from pathlib import Path
from app.agent.nodes.executor import executor_node
from app.agent.state import create_initial_agent_state


def test_executor_node_repo_discovery():
    root = str(Path(__file__).resolve().parent.parent.parent)
    state = create_initial_agent_state(
        job_id="test-exec-01",
        repo_path=root,
        task_prompt="Audit repo",
        mode="AUDIT",
    )
    state["plan_steps"] = [
        {"step_index": 1, "step_name": "Repo Scan", "tool_name": "repo_discovery", "tool_args": {}},
        {"step_index": 2, "step_name": "AST Scan", "tool_name": "ast_parser", "tool_args": {}},
    ]
    state["current_step_idx"] = 0

    # Execute Step 1
    result1 = asyncio.run(executor_node(state))
    assert result1["current_step_idx"] == 1
    assert "repo_meta" in result1
    assert result1["repo_meta"]["is_valid"] is True
    assert len(result1["tool_history"]) == 1
    assert result1["tool_history"][0]["tool_name"] == "repo_discovery"

    # Update state and execute Step 2
    state["current_step_idx"] = 1
    state["tool_history"] = result1["tool_history"]
    result2 = asyncio.run(executor_node(state))
    assert result2["current_step_idx"] == 2
    assert "dead_code_candidates" in result2
    assert len(result2["tool_history"]) == 2
    assert result2["tool_history"][1]["tool_name"] == "ast_parser"
