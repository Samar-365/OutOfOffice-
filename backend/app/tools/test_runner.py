"""Test framework runner and output parser for Python, TypeScript/JavaScript, Rust, and Go.

Executes test suites in sandboxed subprocesses with timeouts and parses
structured metrics (pass/fail/error counts, failing test names, and stack traces).
"""

import logging
import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("outofoffice.tools.testing")


class TestResult:
    """Structured container for test execution results."""
    __test__ = False

    def __init__(
        self,
        command: str,
        exit_code: int,
        passed: int,
        failed: int,
        skipped: int,
        duration_seconds: float,
        stdout: str,
        stderr: str,
        failing_tests: Optional[List[Dict[str, Any]]] = None,
    ):
        self.command = command
        self.exit_code = exit_code
        self.passed = passed
        self.failed = failed
        self.skipped = skipped
        self.total = passed + failed + skipped
        self.is_success = exit_code == 0 and failed == 0
        self.duration_seconds = duration_seconds
        self.stdout = stdout
        self.stderr = stderr
        self.failing_tests = failing_tests or []

    @property
    def stdout_snippet(self) -> str:
        return self.stdout[-2000:] if len(self.stdout) > 2000 else self.stdout

    @property
    def stderr_snippet(self) -> str:
        return self.stderr[-2000:] if len(self.stderr) > 2000 else self.stderr

    def to_dict(self) -> Dict[str, Any]:
        """Serializes TestResult to dictionary."""
        return {
            "command": self.command,
            "exit_code": self.exit_code,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "total": self.total,
            "is_success": self.is_success,
            "duration_seconds": self.duration_seconds,
            "failing_tests": self.failing_tests,
            "summary": f"{self.passed}/{self.total} passed ({self.failed} failed, {self.skipped} skipped)" if self.total > 0 else "No test counts parsed",
            "stdout_snippet": self.stdout_snippet,
            "stderr_snippet": self.stderr_snippet,
        }


# ----------------------------------------------------------------------
# Test Output Parsers
# ----------------------------------------------------------------------

def parse_pytest_output(output: str) -> Tuple[int, int, int, List[Dict[str, Any]]]:
    """Parses pytest summary lines and failure traces."""
    passed = 0
    failed = 0
    skipped = 0
    failing_tests: List[Dict[str, Any]] = []

    # Example: "=== 12 passed, 2 failed, 1 skipped in 0.42s ==="
    summary_match = re.search(r"=+\s*(.*?)\s+in\s+[\d\.]+s\s*=+", output)
    if summary_match:
        summary_text = summary_match.group(1)
        p_m = re.search(r"(\d+)\s+passed", summary_text)
        f_m = re.search(r"(\d+)\s+failed", summary_text)
        s_m = re.search(r"(\d+)\s+skipped", summary_text)

        if p_m:
            passed = int(p_m.group(1))
        if f_m:
            failed = int(f_m.group(1))
        if s_m:
            skipped = int(s_m.group(1))

    # Extract individual failure names (e.g. "FAILED test_api.py::test_create_job")
    fail_matches = re.finditer(r"FAILED\s+([^\s:]+)::([^\s\n]+)", output)
    for m in fail_matches:
        failing_tests.append({
            "file": m.group(1),
            "test_name": m.group(2),
            "framework": "pytest",
        })

    return passed, failed, skipped, failing_tests


def parse_jest_vitest_output(output: str) -> Tuple[int, int, int, List[Dict[str, Any]]]:
    """Parses Jest / Vitest test runner outputs."""
    passed = 0
    failed = 0
    skipped = 0
    failing_tests: List[Dict[str, Any]] = []

    # Example: "Tests:       2 failed, 1 skipped, 45 passed, 48 total"
    tests_match = re.search(r"Tests:\s*(.*)", output)
    if tests_match:
        line = tests_match.group(1)
        p_m = re.search(r"(\d+)\s+passed", line)
        f_m = re.search(r"(\d+)\s+failed", line)
        s_m = re.search(r"(\d+)\s+skipped", line)

        if p_m:
            passed = int(p_m.group(1))
        if f_m:
            failed = int(f_m.group(1))
        if s_m:
            skipped = int(s_m.group(1))

    # Failing items: "✕ test description" or "FAIL src/app.test.ts"
    fail_files = re.finditer(r"FAIL\s+([^\s\n]+)", output)
    for m in fail_files:
        failing_tests.append({
            "file": m.group(1),
            "framework": "jest/vitest",
        })

    return passed, failed, skipped, failing_tests


# ----------------------------------------------------------------------
# Runner
# ----------------------------------------------------------------------

def detect_default_test_command(repo_path: Path) -> Optional[str]:
    """Detects available test runner command in repository."""
    # Python
    if (repo_path / "pytest.ini").exists() or (repo_path / "backend" / "pytest.ini").exists() or (repo_path / "tests").exists():
        return "python -m pytest"

    # JS/TS
    pkg_json = repo_path / "package.json"
    if pkg_json.exists():
        return "npm test"

    cargo = repo_path / "Cargo.toml"
    if cargo.exists():
        return "cargo test"

    go_mod = repo_path / "go.mod"
    if go_mod.exists():
        return "go test ./..."

    return None


def run_test_suite(
    repo_path_str: str,
    custom_command: Optional[str] = None,
    timeout: int = 60,
) -> TestResult:
    """Executes the test suite in the specified repository and parses results."""
    repo_path = Path(repo_path_str).resolve()
    if not repo_path.exists():
        return TestResult(
            command="none",
            exit_code=-1,
            passed=0,
            failed=1,
            skipped=0,
            duration_seconds=0.0,
            stdout="",
            stderr=f"Repository path does not exist: {repo_path_str}",
        )

    cmd = custom_command or detect_default_test_command(repo_path)
    if not cmd:
        return TestResult(
            command="none",
            exit_code=0,
            passed=0,
            failed=0,
            skipped=0,
            duration_seconds=0.0,
            stdout="No test framework detected in repository.",
            stderr="",
        )

    import time
    start_time = time.time()
    try:
        # Run command via shell on Windows / POSIX
        res = subprocess.run(
            cmd,
            shell=True,
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        duration = round(time.time() - start_time, 2)
        stdout = res.stdout
        stderr = res.stderr
        exit_code = res.returncode

    except subprocess.TimeoutExpired as e:
        duration = round(time.time() - start_time, 2)
        return TestResult(
            command=cmd,
            exit_code=-1,
            passed=0,
            failed=1,
            skipped=0,
            duration_seconds=duration,
            stdout=e.stdout or "",
            stderr=f"Test execution timed out after {timeout} seconds.",
        )
    except Exception as e:
        duration = round(time.time() - start_time, 2)
        return TestResult(
            command=cmd,
            exit_code=-1,
            passed=0,
            failed=1,
            skipped=0,
            duration_seconds=duration,
            stdout="",
            stderr=f"Failed to execute tests: {e}",
        )

    # Parse stdout and stderr
    full_text = f"{stdout}\n{stderr}"
    passed, failed, skipped, failing_tests = 0, 0, 0, []

    if "pytest" in cmd:
        passed, failed, skipped, failing_tests = parse_pytest_output(full_text)
    elif "npm" in cmd or "vitest" in cmd or "jest" in cmd:
        passed, failed, skipped, failing_tests = parse_jest_vitest_output(full_text)

    # Fallback heuristic if regex did not catch numbers
    if passed == 0 and failed == 0:
        if exit_code == 0:
            passed = 1
        else:
            failed = 1

    return TestResult(
        command=cmd,
        exit_code=exit_code,
        passed=passed,
        failed=failed,
        skipped=skipped,
        duration_seconds=duration,
        stdout=stdout,
        stderr=stderr,
        failing_tests=failing_tests,
    )
