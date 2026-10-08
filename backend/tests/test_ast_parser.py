"""Unit tests for AST and symbol extraction tool."""

import pytest
from pathlib import Path
from app.tools.ast_parser import (
    CodeSymbol,
    extract_symbols_from_file,
    build_symbol_table,
    parse_python_file,
    parse_typescript_javascript_file,
)


def test_python_ast_parsing(tmp_path):
    py_code = '''
def active_helper(a: int, b: str) -> bool:
    """A helpful function."""
    return True

async def async_worker():
    pass

class TaskProcessor:
    def process(self):
        pass
'''
    py_file = tmp_path / "sample.py"
    py_file.write_text(py_code, encoding="utf-8")

    symbols = parse_python_file(py_file, "sample.py")
    names = {s.name: s for s in symbols}

    assert "active_helper" in names
    assert names["active_helper"].kind == "function"
    assert names["active_helper"].is_exported is True
    assert "a" in names["active_helper"].parameters

    assert "async_worker" in names
    assert names["async_worker"].kind == "async_function"

    assert "TaskProcessor" in names
    assert names["TaskProcessor"].kind == "class"


def test_typescript_parsing(tmp_path):
    ts_code = '''
export function calculateScore(items: number[]): number {
    return 100;
}

export const formatUserName = (firstName: string, lastName: string) => {
    return firstName + " " + lastName;
};

export interface UserProfile {
    id: string;
}

export class AnalyticsService {}
'''
    ts_file = tmp_path / "service.ts"
    ts_file.write_text(ts_code, encoding="utf-8")

    symbols = parse_typescript_javascript_file(ts_file, "service.ts")
    names = {s.name: s for s in symbols}

    assert "calculateScore" in names
    assert names["calculateScore"].is_exported is True

    assert "formatUserName" in names
    assert names["formatUserName"].is_exported is True

    assert "UserProfile" in names
    assert names["UserProfile"].kind == "interface"

    assert "AnalyticsService" in names
    assert names["AnalyticsService"].kind == "class"


def test_build_symbol_table_current_repo():
    root = str(Path(__file__).resolve().parent.parent.parent)
    table = build_symbol_table(root)
    assert table["total_symbols"] > 0
    assert table["exported_symbols_count"] > 0
