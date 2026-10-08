"""Unit tests for the fixer and validation cycle LangGraph node."""

import asyncio
import subprocess
from pathlib import Path
from app.agent.nodes.fixer import fixer_node
from app.agent.state import create_initial_agent_state


def _init_test_git_repo(repo_dir: Path):
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@runner.local"], cwd=str(repo_dir), capture_output=True, check=True)
    (repo_dir / "app.py").write_text("def run():\n    return 42\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo_dir), capture_output=True, check=True)


def test_fixer_node_audit_mode(tmp_path):
    _init_test_git_repo(tmp_path)
    state = create_initial_agent_state(
        job_id="test-fix-audit",
        repo_path=str(tmp_path),
        task_prompt="Audit only",
        mode="AUDIT",
    )
    state["findings"] = [{"title": "Unused code", "is_safe_to_fix": True}]

    result = asyncio.run(fixer_node(state))
    # In AUDIT mode, diffs must remain empty
    assert result["diffs"] == []


def test_fixer_node_fix_mode_branch_creation(tmp_path):
    _init_test_git_repo(tmp_path)
    state = create_initial_agent_state(
        job_id="test-fix-active",
        repo_path=str(tmp_path),
        task_prompt="Fix safe issues",
        mode="FIX",
    )
    state["findings"] = []

    result = asyncio.run(fixer_node(state))
    assert "agent_branch" in result
    assert result["agent_branch"].startswith("agent/outofoffice-")
    assert result["base_branch"] == "main"
