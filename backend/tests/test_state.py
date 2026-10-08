"""Unit tests for agent state and initialization."""

import pytest
from app.agent.state import AgentState, create_initial_agent_state


def test_create_initial_agent_state():
    state = create_initial_agent_state(
        job_id="job-12345",
        repo_path="/path/to/repo",
        task_prompt="Find unused code",
        mode="FIX",
        model_name="gemma2:9b",
    )
    assert state["job_id"] == "job-12345"
    assert state["mode"] == "FIX"
    assert state["model_name"] == "gemma2:9b"
    assert state["status"] == "RUNNING"
    assert state["current_step_idx"] == 0
    assert isinstance(state["findings"], list)
    assert isinstance(state["diffs"], list)
    assert state["away_start_timestamp"] > 0
