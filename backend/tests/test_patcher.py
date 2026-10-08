"""Unit tests for surgical file patcher and rollback engine."""

import pytest
from pathlib import Path
from app.tools.patcher import (
    apply_surgical_patch,
    rollback_patch,
    generate_unified_diff,
)


def test_apply_valid_surgical_patch(tmp_path):
    target_file = tmp_path / "calc.py"
    target_file.write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")

    result = apply_surgical_patch(
        repo_path_str=str(tmp_path),
        file_rel_path="calc.py",
        target_content="return a - b",
        replacement_content="return a + b",
    )
    assert result.success is True
    assert "return a + b" in result.patched_content
    assert target_file.read_text(encoding="utf-8") == "def add(a, b):\n    return a + b\n"
    assert "--- a/calc.py" in result.diff_unified
    assert "+    return a + b" in result.diff_unified

    # Test rollback
    ok = rollback_patch(str(tmp_path), "calc.py", result.original_content)
    assert ok is True
    assert target_file.read_text(encoding="utf-8") == "def add(a, b):\n    return a - b\n"


def test_reject_invalid_syntax_patch(tmp_path):
    target_file = tmp_path / "valid.py"
    target_file.write_text("def run():\n    return 42\n", encoding="utf-8")

    # Try introducing broken python syntax
    result = apply_surgical_patch(
        repo_path_str=str(tmp_path),
        file_rel_path="valid.py",
        target_content="return 42",
        replacement_content="return (42",  # Unclosed paren syntax error
        verify_syntax=True,
    )
    assert result.success is False
    assert "SyntaxError" in result.error
    # Content must remain uncorrupted
    assert target_file.read_text(encoding="utf-8") == "def run():\n    return 42\n"


def test_reject_protected_files(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("SECRET=123\n", encoding="utf-8")

    result = apply_surgical_patch(
        repo_path_str=str(tmp_path),
        file_rel_path=".env",
        target_content="SECRET=123",
        replacement_content="SECRET=456",
    )
    assert result.success is False
    assert "Unsafe or protected" in result.error
