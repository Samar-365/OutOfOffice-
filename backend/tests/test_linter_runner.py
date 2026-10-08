"""Unit tests for static analysis and linter runner tool."""

import pytest
from pathlib import Path
from app.tools.linter_runner import (
    LintIssue,
    run_static_analysis,
    scan_python_syntax_and_annotations,
    scan_ts_js_annotations,
)


def test_scan_python_syntax_error(tmp_path):
    bad_py = tmp_path / "broken.py"
    bad_py.write_text("def broken_syntax(\n    return 42\n", encoding="utf-8")

    issues = scan_python_syntax_and_annotations(tmp_path)
    syntax_issues = [i for i in issues if i.error_code == "E999"]
    assert len(syntax_issues) >= 1
    assert syntax_issues[0].severity == "HIGH"
    assert "SyntaxError" in syntax_issues[0].message


def test_scan_code_annotations(tmp_path):
    py_file = tmp_path / "service.py"
    py_file.write_text("# TODO: optimize database connection\n# FIXME: handle token expiry\n", encoding="utf-8")

    ts_file = tmp_path / "component.tsx"
    ts_file.write_text("// BUG: modal closes on drag\n", encoding="utf-8")

    issues = run_static_analysis(str(tmp_path))
    assert issues["total_issues"] >= 3
    tags = {i["error_code"] for i in issues["issues"]}
    assert "TODO" in tags
    assert "FIXME" in tags
    assert "BUG" in tags
