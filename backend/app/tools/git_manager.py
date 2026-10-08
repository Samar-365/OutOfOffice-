"""Git Branch & Diff Manager for isolated Fix Mode workflows.

Safely creates dedicated agent branches, generates unified diffs,
commits validated patches, and rolls back regressions without pushing to remotes.
"""

import datetime
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("outofoffice.tools.git")


class GitManager:
    """Manages Git branch isolation, diff generation, and workspace rollbacks."""

    def __init__(self, repo_path_str: str):
        self.repo_path = Path(repo_path_str).resolve()
        if not self.repo_path.exists():
            raise ValueError(f"Repository directory does not exist: {repo_path_str}")

    def _run_git(self, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        """Runs a git command in the repository workspace."""
        try:
            res = subprocess.run(
                ["git"] + args,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            logger.error(f"Error running git {' '.join(args)}: {e}")
            return -1, "", str(e)

    def get_current_branch(self) -> str:
        """Returns the current checked out Git branch."""
        code, stdout, _ = self._run_git(["rev-parse", "--abbrev-ref", "HEAD"])
        return stdout if code == 0 and stdout else "main"

    def has_uncommitted_changes(self) -> bool:
        """Checks if the working tree has uncommitted modifications."""
        code, stdout, _ = self._run_git(["status", "--porcelain"])
        return bool(stdout) if code == 0 else False

    def create_isolated_branch(self, branch_name: Optional[str] = None) -> Tuple[bool, str, str]:
        """Creates and checks out a new isolated agent branch (e.g. agent/outofoffice-20261009-030400)."""
        base_branch = self.get_current_branch()
        if not branch_name:
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            branch_name = f"{settings.AGENT_BRANCH_PREFIX}{timestamp}"

        # Create and checkout new branch
        code, stdout, stderr = self._run_git(["checkout", "-b", branch_name])
        if code != 0:
            logger.error(f"Failed to create agent branch {branch_name}: {stderr}")
            return False, base_branch, f"Failed to checkout branch: {stderr}"

        logger.info(f"Created isolated branch '{branch_name}' based on '{base_branch}'")
        return True, base_branch, branch_name

    def get_unified_diff(self, base_branch: Optional[str] = None) -> str:
        """Generates unified diff comparing working tree/branch against base_branch."""
        if base_branch:
            code, stdout, _ = self._run_git(["diff", f"{base_branch}...HEAD"])
            if code == 0 and stdout:
                return stdout

        # Fallback to current working tree diff
        code, stdout, _ = self._run_git(["diff", "HEAD"])
        if code == 0:
            return stdout

        code, stdout, _ = self._run_git(["diff"])
        return stdout if code == 0 else ""

    def stage_and_commit(self, message: str, author_name: str = "OutOfOffice AI", author_email: str = "agent@outofoffice.local") -> Tuple[bool, str]:
        """Stages all changes and creates a local commit on the agent branch."""
        # Stage all changes
        code, _, stderr = self._run_git(["add", "-A"])
        if code != 0:
            return False, f"Failed to stage changes: {stderr}"

        # Commit
        author_flag = f"{author_name} <{author_email}>"
        code, stdout, stderr = self._run_git(["commit", "--author", author_flag, "-m", message])
        if code != 0:
            # Check if clean working tree
            if "nothing to commit" in stderr.lower() or "nothing to commit" in stdout.lower():
                return True, "Nothing to commit (working tree clean)"
            return False, f"Commit failed: {stderr}"

        return True, stdout

    def rollback_to_branch(self, base_branch: str) -> Tuple[bool, str]:
        """Discards uncommitted changes and checks out the base branch."""
        # Discard uncommitted changes
        self._run_git(["reset", "--hard", "HEAD"])
        self._run_git(["clean", "-fd"])

        # Checkout original branch
        code, stdout, stderr = self._run_git(["checkout", base_branch])
        if code != 0:
            return False, f"Failed to checkout {base_branch}: {stderr}"

        return True, f"Successfully rolled back to {base_branch}"

    def merge_into_branch(self, agent_branch: str, target_branch: str) -> Tuple[bool, str]:
        """Merges agent_branch into target_branch locally."""
        # Checkout target branch
        code, _, stderr = self._run_git(["checkout", target_branch])
        if code != 0:
            return False, f"Failed to checkout {target_branch}: {stderr}"

        # Merge
        code, stdout, stderr = self._run_git(["merge", "--no-ff", agent_branch, "-m", f"Merge {agent_branch} by OutOfOffice AI"])
        if code != 0:
            # Abort merge on conflict
            self._run_git(["merge", "--abort"])
            return False, f"Merge conflict or failure: {stderr}"

        return True, f"Successfully merged {agent_branch} into {target_branch}"
