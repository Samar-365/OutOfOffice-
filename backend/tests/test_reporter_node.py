"""Unit tests for the reporter and health score synthesis node."""

import asyncio
from app.agent.nodes.reporter import reporter_node, calculate_health_score, _generate_fallback_report
from app.agent.state import create_initial_agent_state


def test_calculate_health_score_all_green():
    test_results = {"passed": 47, "failed": 0, "total": 47}
    findings = []
    diffs = [{"file": "src/utils.ts"}]
    score = calculate_health_score(test_results, findings, diffs)
    assert score == 100


def test_calculate_health_score_with_penalties():
    test_results = {"passed": 40, "failed": 2, "total": 42}
    findings = [
        {"severity": "HIGH", "is_fixed": False},
        {"severity": "MEDIUM", "is_fixed": False},
    ]
    diffs = []
    score = calculate_health_score(test_results, findings, diffs)
    # 100 - 40 (tests) - 15 (high) - 4 (med) = 41
    assert score == 41


def test_reporter_node_execution():
    state = create_initial_agent_state(
        job_id="test-rep-01",
        repo_path="/fake/repo",
        task_prompt="Audit and clean code",
        mode="FIX",
    )
    state["repo_meta"] = {"repo_name": "shop-app", "file_count": 88}
    state["findings"] = [{"title": "Dead code in auth.ts", "severity": "MEDIUM"}]
    state["diffs"] = [{"file_path": "src/auth.ts"}]
    state["test_results"] = {"passed": 20, "failed": 0, "total": 20}

    result = asyncio.run(reporter_node(state))
    assert result["status"] == "COMPLETED"
    assert "health_score" in result
    assert result["health_score"] > 80
    assert "touching grass" in result["voice_brief_script"]
    assert "OutOfOffice AI" in result["final_report_markdown"]
