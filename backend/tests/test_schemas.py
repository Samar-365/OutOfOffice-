"""Unit tests for agent structured output schemas and JSON parsing utilities."""

import pytest
from app.agent.schemas import (
    PlanItem,
    PlanOutput,
    InvestigationOutput,
    PatchOutput,
    ReportOutput,
    extract_json_block,
    repair_json_string,
    parse_and_validate_json,
)


def test_plan_output_parsing():
    raw_markdown = """
    Here is the execution plan for your repository:
    ```json
    {
      "summary": "Analyze repository, find unused exports, and run tests",
      "estimated_minutes": 6,
      "steps": [
        {
          "step_index": 1,
          "step_name": "Repository Discovery",
          "tool_name": "repo_discovery",
          "tool_args": {},
          "rationale": "Scan manifests and directory structure"
        },
        {
          "step_index": 2,
          "step_name": "Run Test Suite",
          "tool_name": "test_runner",
          "tool_args": {"command": "npm test"},
          "rationale": "Verify baseline status"
        }
      ]
    }
    ```
    """
    plan = parse_and_validate_json(raw_markdown, PlanOutput)
    assert plan.summary == "Analyze repository, find unused exports, and run tests"
    assert plan.estimated_minutes == 6
    assert len(plan.steps) == 2
    assert plan.steps[0].tool_name == "repo_discovery"
    assert plan.steps[1].tool_args == {"command": "npm test"}


def test_json_repair_trailing_commas():
    malformed = '{"summary": "Test", "estimated_minutes": 3, "steps": [{"step_index": 1, "step_name": "Scan", "tool_name": "ast_parser", "tool_args": {}, "rationale": "Rationale",},],}'
    plan = parse_and_validate_json(malformed, PlanOutput)
    assert plan.summary == "Test"
    assert len(plan.steps) == 1


def test_investigation_output():
    raw_json = """
    {
      "issue_title": "Dead function legacyAuth() in auth.ts",
      "severity": "MEDIUM",
      "category": "DEAD_CODE",
      "file_path": "src/auth.ts",
      "line_number": 48,
      "root_cause": "Function was replaced by oauth2Auth but never removed",
      "evidence": "0 callers found across all files in repository",
      "confidence": "HIGH",
      "is_safe_to_fix": true,
      "fix_approach": "Remove function and its unused imports"
    }
    """
    investigation = parse_and_validate_json(raw_json, InvestigationOutput)
    assert investigation.category == "DEAD_CODE"
    assert investigation.is_safe_to_fix is True
    assert investigation.line_number == 48


def test_report_output():
    raw_json = """
    {
      "health_score": 94,
      "summary": "Autonomous audit and safe fix cycle completed.",
      "files_analyzed_count": 82,
      "issues_found_count": 4,
      "safe_fixes_applied_count": 2,
      "test_summary": "47/47 tests passing",
      "key_findings": ["Removed 2 dead functions", "Resolved 1 type error"],
      "voice_brief_script": "Welcome back! While you spent 32 minutes outside touching grass, I analyzed 82 files and validated your build."
    }
    """
    report = parse_and_validate_json(raw_json, ReportOutput)
    assert report.health_score == 94
    assert report.safe_fixes_applied_count == 2
    assert "touching grass" in report.voice_brief_script
