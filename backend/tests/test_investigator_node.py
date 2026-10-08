"""Unit tests for the investigator LangGraph node."""

import asyncio
from pathlib import Path
from app.agent.nodes.investigator import investigator_node, _read_code_snippet
from app.agent.state import create_initial_agent_state


def test_read_code_snippet(tmp_path):
    f = tmp_path / "app.py"
    f.write_text("\n".join(f"line {i}" for i in range(1, 30)), encoding="utf-8")

    snippet = _read_code_snippet(tmp_path, "app.py", center_line=15, context_lines=6)
    assert "15: line 15" in snippet
    assert len(snippet.splitlines()) <= 7


def test_investigator_node_compilation(tmp_path):
    state = create_initial_agent_state(
        job_id="test-inv-01",
        repo_path=str(tmp_path),
        task_prompt="Investigate issues",
        mode="AUDIT",
    )
    state["dead_code_candidates"] = [
        {"symbol_name": "unusedHelper", "file_path": "src/calc.ts", "line_start": 22, "evidence": "0 callers found"}
    ]
    state["static_issues"] = [
        {"file_path": "src/calc.ts", "line_number": 5, "severity": "MEDIUM", "message": "TODO: add unit test"}
    ]
    state["test_results"] = {
        "failing_tests": [{"file": "src/test.py", "test_name": "test_subtract"}]
    }

    result = asyncio.run(investigator_node(state))
    assert "findings" in result
    assert len(result["findings"]) == 3

    categories = {f["category"] for f in result["findings"]}
    assert "DEAD_CODE" in categories
    assert "LINT_ERROR" in categories
    assert "TEST_FAILURE" in categories
