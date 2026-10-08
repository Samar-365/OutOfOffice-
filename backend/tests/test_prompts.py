"""Unit tests for prompt matrix templates."""

import pytest
from app.agent.prompts import (
    SYSTEM_PROMPT_AGENT_CORE,
    build_planner_prompt,
    build_investigation_prompt,
    build_fixer_prompt,
    build_reporter_prompt,
)


def test_planner_prompt_generation():
    repo_meta = {
        "project_type": "React (TypeScript)",
        "detected_languages": ["TypeScript", "JavaScript"],
        "manifest_files": ["package.json"],
        "test_framework": "Vitest",
        "file_count": 84,
    }
    prompt = build_planner_prompt(
        task_prompt="Find dead code and run vitest",
        repo_meta=repo_meta,
        mode="FIX",
    )
    assert "React (TypeScript)" in prompt
    assert "Vitest" in prompt
    assert "84" in prompt
    assert "FIX" in prompt
    assert "repo_discovery" in prompt


def test_investigation_prompt_generation():
    prompt = build_investigation_prompt(
        issue_type="DEAD_CODE",
        target_file="src/utils.ts",
        error_output_or_symbol="function legacyFormat()",
        code_context="export function legacyFormat() { return null; }",
        references_found=0,
    )
    assert "src/utils.ts" in prompt
    assert "References Found across Codebase: 0" in prompt
    assert "legacyFormat" in prompt


def test_fixer_prompt_generation():
    prompt = build_fixer_prompt(
        file_path="src/utils.ts",
        issue_description="Unused dead function",
        fix_approach="Remove the function export",
        file_content="export function unused() {}\nexport function active() {}",
    )
    assert "src/utils.ts" in prompt
    assert "original_code_block" in prompt
    assert "replacement_code_block" in prompt


def test_reporter_prompt_generation():
    repo_meta = {"file_count": 112}
    findings = [{"title": "Dead code", "file": "src/utils.ts"}]
    diffs = [{"file": "src/utils.ts"}]
    test_results = {"passed": 32, "failed": 0, "total": 32}

    prompt = build_reporter_prompt(
        task_prompt="Run audit",
        repo_meta=repo_meta,
        steps_executed=[],
        findings=findings,
        diffs_applied=diffs,
        test_results=test_results,
        away_minutes=42.0,
    )
    assert "42 minutes" in prompt
    assert "32/32 tests passed" in prompt
    assert "voice_brief_script" in prompt
