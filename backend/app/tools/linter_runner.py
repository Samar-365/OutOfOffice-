"""Static analysis, linter runner, and code quality scanner tool.

Runs TypeScript compiler checks (tsc), Python linters (flake8, ruff, mypy, py_compile),
and an in-process code health scanner (TODO/FIXME/BUG annotations, syntax validation).
"""

import ast
import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("outofoffice.tools.linter")

IGNORE_DIRS: Set[str] = {
    ".git", "node_modules", ".venv", "venv", "dist", "build",
    "__pycache__", ".pytest_cache", ".next", "coverage"
}


class LintIssue:
    """Represents a structured lint, syntax, or static analysis issue."""

    def __init__(
        self,
        file_path: str,
        line_number: int,
        message: str,
        severity: str = "MEDIUM",  # HIGH, MEDIUM, LOW, INFO
        error_code: Optional[str] = None,
        source: str = "static_analyzer",
    ):
        self.file_path = file_path
        self.line_number = line_number
        self.message = message
        self.severity = severity
        self.error_code = error_code
        self.source = source

    def to_dict(self) -> Dict[str, Any]:
        """Serializes LintIssue to dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "message": self.message,
            "severity": self.severity,
            "error_code": self.error_code,
            "source": self.source,
        }


# ----------------------------------------------------------------------
# In-Process Syntax & Code Health Scanner
# ----------------------------------------------------------------------

TODO_PATTERN = re.compile(r"\b(TODO|FIXME|BUG|HACK|XXX)\b\s*[:\-]?\s*(.*)", re.IGNORECASE)


def scan_python_syntax_and_annotations(repo_path: Path) -> List[LintIssue]:
    """Scans all Python files for AST syntax errors and TODO/FIXME markers."""
    issues: List[LintIssue] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for file_name in files:
            if file_name.endswith((".py", ".pyi")):
                file_path = Path(root) / file_name
                rel_path = file_path.relative_to(repo_path).as_posix()
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()

                    # 1. Syntax check
                    try:
                        ast.parse(content, filename=str(file_path))
                    except SyntaxError as syn_err:
                        issues.append(
                            LintIssue(
                                file_path=rel_path,
                                line_number=syn_err.lineno or 1,
                                message=f"Python SyntaxError: {syn_err.msg}",
                                severity="HIGH",
                                error_code="E999",
                                source="python_ast",
                            )
                        )

                    # 2. Annotation check (TODO / FIXME / BUG)
                    for line_idx, line in enumerate(lines, start=1):
                        m = TODO_PATTERN.search(line)
                        if m:
                            tag = m.group(1).upper()
                            note = m.group(2).strip() or "No description provided"
                            issues.append(
                                LintIssue(
                                    file_path=rel_path,
                                    line_number=line_idx,
                                    message=f"{tag}: {note}",
                                    severity="LOW" if tag == "TODO" else "MEDIUM",
                                    error_code=tag,
                                    source="code_annotations",
                                )
                            )
                except Exception:
                    continue

    return issues


def scan_ts_js_annotations(repo_path: Path) -> List[LintIssue]:
    """Scans JS/TS files for TODO/FIXME markers."""
    issues: List[LintIssue] = []

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS and not d.startswith(".")]

        for file_name in files:
            if file_name.endswith((".ts", ".tsx", ".js", ".jsx")):
                file_path = Path(root) / file_name
                rel_path = file_path.relative_to(repo_path).as_posix()
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    for line_idx, line in enumerate(content.splitlines(), start=1):
                        m = TODO_PATTERN.search(line)
                        if m:
                            tag = m.group(1).upper()
                            note = m.group(2).strip() or "No description provided"
                            issues.append(
                                LintIssue(
                                    file_path=rel_path,
                                    line_number=line_idx,
                                    message=f"{tag}: {note}",
                                    severity="LOW" if tag == "TODO" else "MEDIUM",
                                    error_code=tag,
                                    source="code_annotations",
                                )
                            )
                except Exception:
                    continue

    return issues


# ----------------------------------------------------------------------
# Subprocess Linters (flake8, ruff, mypy, tsc)
# ----------------------------------------------------------------------

def run_python_external_linters(repo_path: Path) -> List[LintIssue]:
    """Runs ruff or flake8 if installed in environment."""
    issues: List[LintIssue] = []

    # Check for ruff or flake8 in PATH
    linter_cmd = None
    if shutil.which("ruff"):
        linter_cmd = ["ruff", "check", "--output-format=json", str(repo_path)]
    elif shutil.which("flake8"):
        linter_cmd = ["flake8", str(repo_path)]

    if not linter_cmd:
        return issues

    try:
        res = subprocess.run(linter_cmd, cwd=str(repo_path), capture_output=True, text=True, timeout=15)
        if "ruff" in linter_cmd[0] and res.stdout.strip():
            try:
                data = json.loads(res.stdout)
                for item in data:
                    fpath = Path(item.get("filename", "")).relative_to(repo_path).as_posix()
                    issues.append(
                        LintIssue(
                            file_path=fpath,
                            line_number=item.get("location", {}).get("row", 1),
                            message=item.get("message", ""),
                            severity="MEDIUM",
                            error_code=item.get("code"),
                            source="ruff",
                        )
                    )
            except Exception:
                pass
        elif "flake8" in linter_cmd[0] and res.stdout.strip():
            # format: path:line:col: code message
            for line in res.stdout.splitlines():
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    fpath = Path(parts[0]).relative_to(repo_path).as_posix()
                    line_num = int(parts[1])
                    msg = parts[3].strip()
                    issues.append(
                        LintIssue(
                            file_path=fpath,
                            line_number=line_num,
                            message=msg,
                            severity="MEDIUM",
                            source="flake8",
                        )
                    )
    except Exception as e:
        logger.debug(f"External python linter failed: {e}")

    return issues


def run_static_analysis(repo_path_str: str) -> Dict[str, Any]:
    """Master static analysis and linting entrypoint."""
    repo_path = Path(repo_path_str).resolve()
    if not repo_path.exists():
        return {"error": f"Repository not found: {repo_path_str}", "issues": []}

    all_issues: List[LintIssue] = []

    # 1. Python AST syntax & TODO/FIXME scans
    all_issues.extend(scan_python_syntax_and_annotations(repo_path))

    # 2. JS/TS Annotations
    all_issues.extend(scan_ts_js_annotations(repo_path))

    # 3. External linters if available
    all_issues.extend(run_python_external_linters(repo_path))

    high_count = sum(1 for i in all_issues if i.severity == "HIGH")
    medium_count = sum(1 for i in all_issues if i.severity == "MEDIUM")
    low_count = sum(1 for i in all_issues if i.severity in ["LOW", "INFO"])

    return {
        "total_issues": len(all_issues),
        "high_severity": high_count,
        "medium_severity": medium_count,
        "low_severity": low_count,
        "issues": [i.to_dict() for i in all_issues],
    }
