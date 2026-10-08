"""Unit tests for Git branch and diff manager tool."""

import os
import subprocess
import pytest
from pathlib import Path
from app.tools.git_manager import GitManager


def _init_test_git_repo(repo_dir: Path):
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@runner.local"], cwd=str(repo_dir), capture_output=True, check=True)
    
    # Create initial file
    initial_file = repo_dir / "index.txt"
    initial_file.write_text("initial content\n", encoding="utf-8")
    subprocess.run(["git", "add", "index.txt"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=str(repo_dir), capture_output=True, check=True)


def test_git_manager_branch_creation_and_diff(tmp_path):
    _init_test_git_repo(tmp_path)
    git_mgr = GitManager(str(tmp_path))

    assert git_mgr.get_current_branch() == "main"
    assert git_mgr.has_uncommitted_changes() is False

    # Create isolated agent branch
    ok, base_branch, agent_branch = git_mgr.create_isolated_branch("agent/test-branch-01")
    assert ok is True
    assert base_branch == "main"
    assert agent_branch == "agent/test-branch-01"
    assert git_mgr.get_current_branch() == "agent/test-branch-01"

    # Make a modification
    (tmp_path / "index.txt").write_text("updated content by agent\n", encoding="utf-8")
    diff = git_mgr.get_unified_diff()
    assert "updated content by agent" in diff

    # Commit change
    ok, msg = git_mgr.stage_and_commit("fix: update index.txt")
    assert ok is True

    # Rollback to main
    ok, rollback_msg = git_mgr.rollback_to_branch("main")
    assert ok is True
    assert git_mgr.get_current_branch() == "main"
    assert (tmp_path / "index.txt").read_text(encoding="utf-8") == "initial content\n"
