"""Unit tests for search engine and symbol reference finder tool."""

import pytest
from pathlib import Path
from app.tools.search_engine import (
    search_code,
    find_symbol_references,
    find_dead_code_candidates,
)


def test_search_code_finds_strings():
    root = str(Path(__file__).resolve().parent.parent.parent)
    matches = search_code(root, "OutOfOffice AI", case_sensitive=True, max_results=10)
    assert len(matches) > 0
    assert any("config.py" in m["file_path"] or "srs.txt" in m["file_path"] for m in matches)


def test_find_symbol_references(tmp_path):
    f1 = tmp_path / "util.py"
    f1.write_text("def helper_target():\n    return 42\n", encoding="utf-8")

    f2 = tmp_path / "main.py"
    f2.write_text("from util import helper_target\nval = helper_target()\n", encoding="utf-8")

    ref_info = find_symbol_references(
        repo_path_str=str(tmp_path),
        symbol_name="helper_target",
        defining_file_rel_path="util.py",
        defining_line_start=1,
        defining_line_end=2,
    )
    assert ref_info["external_references_count"] == 2  # import + call in main.py
    assert ref_info["is_unused_candidate"] is False


def test_find_unused_symbol(tmp_path):
    f1 = tmp_path / "orphan.py"
    f1.write_text("def never_called_function():\n    return 'dead'\n", encoding="utf-8")

    ref_info = find_symbol_references(
        repo_path_str=str(tmp_path),
        symbol_name="never_called_function",
        defining_file_rel_path="orphan.py",
        defining_line_start=1,
        defining_line_end=2,
    )
    assert ref_info["external_references_count"] == 0
    assert ref_info["is_unused_candidate"] is True
