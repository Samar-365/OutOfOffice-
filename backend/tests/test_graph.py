"""Unit tests for the complete AgentWorkflow graph execution."""

import asyncio
import subprocess
from pathlib import Path
from app.agent.graph import AgentWorkflow


def _init_test_git_repo(repo_dir: Path):
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@runner.local"], cwd=str(repo_dir), capture_output=True, check=True)
    (repo_dir / "app.py").write_text("def run_task():\n    return 42\n", encoding="utf-8")
    (repo_dir / "requirements.txt").write_text("pytest>=7.0.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "app.py", "requirements.txt"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=str(repo_dir), capture_output=True, check=True)


def test_agent_workflow_audit_mode_execution(tmp_path):
    _init_test_git_repo(tmp_path)
    workflow = AgentWorkflow()

    step_log = []
    def on_step(state, step_name):
        step_log.append(step_name)

    final_state = asyncio.run(
        workflow.execute(
            job_id="test-e2e-audit",
            repo_path=str(tmp_path),
            task_prompt="Audit dead code and check requirements",
            mode="AUDIT",
            on_step_update=on_step,
        )
    )

    assert "COMPLETED" in final_state["status"]
    assert final_state["health_score"] is not None
    assert final_state["health_score"] >= 0
    assert "OutOfOffice AI" in final_state["final_report_markdown"]
    assert len(final_state["tool_history"]) >= 4
    assert len(step_log) >= 5
