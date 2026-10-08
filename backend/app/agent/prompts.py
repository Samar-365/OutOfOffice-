"""System prompts and prompt templates tailored for local Gemma 2 / CodeGemma inference.

Enforces truthfulness, deterministic tool verification, safe surgical modifications,
and the 'Touch Grass' narrative for Hacktoberfest 2026.
"""

from typing import Any, Dict, List, Optional


SYSTEM_PROMPT_AGENT_CORE = """You are OutOfOffice AI, a local-first autonomous software engineer and repository auditor.
Your mission is to autonomously inspect codebases, execute tests, identify dead code and bugs, and synthesize safe fixes while the developer is away ('touching grass').

CRITICAL OPERATIONAL RULES:
1. TRUTHFULNESS & EVIDENCE: Never hallucinate issues. Clearly distinguish between DETERMINISTIC FACTS (e.g. a failing test command or 0 AST references) and PROBABILISTIC OBSERVATIONS.
2. SAFETY FIRST: Never delete configuration files (.gitignore, package.json, tsconfig.json, pyproject.toml). Never perform destructive Git operations.
3. ISOLATED WORKFLOW: All code modifications must be minimal, surgical, and line-bounded.
4. VALIDATION: Every code fix must be validated against the project's test suite.
5. FORMAT COMPLIANCE: Always output valid JSON strictly adhering to the requested schema.
"""


def build_planner_prompt(
    task_prompt: str,
    repo_meta: Dict[str, Any],
    mode: str = "AUDIT",
) -> str:
    """Constructs prompt for the Planning node to decompose a task into structured tool steps."""
    languages = ", ".join(repo_meta.get("detected_languages", [])) or "Unknown"
    manifests = ", ".join(repo_meta.get("manifest_files", [])) or "None"
    test_fw = repo_meta.get("test_framework", "None")
    file_count = repo_meta.get("file_count", 0)
    project_type = repo_meta.get("project_type", "General Codebase")

    return f"""TASK INSTRUCTION:
"{task_prompt}"

REPOSITORY CONTEXT:
- Project Type: {project_type}
- Primary Languages: {languages}
- Manifests: {manifests}
- Detected Test Framework: {test_fw}
- File Count: {file_count}
- Execution Mode: {mode} (AUDIT = Read-only inspection; FIX = Isolated branch modifications + test validation)

AVAILABLE TOOLS:
- `repo_discovery`: Scan directory structure, file hierarchy, and manifests.
- `ast_parser`: Parse Tree-sitter AST to extract exported symbols, functions, classes, and unused declarations.
- `search_engine`: Ripgrep fast code search for symbol references across all files.
- `test_runner`: Run project test suite ({test_fw}) and capture stack traces.
- `linter_runner`: Run static analysis / type check (tsc, flake8, mypy, eslint).
- `patcher`: Apply surgical code changes to an isolated branch (only in FIX mode).
- `reporter`: Synthesize final findings, repository health score (0-100), and ElevenLabs voice briefing.

INSTRUCTIONS:
Generate a structured, logical sequence of steps (4 to 8 steps) to fulfill the task.
Output MUST be a single JSON object matching this schema:
{{
  "summary": "Short 1-2 sentence description of the overall plan",
  "estimated_minutes": 5,
  "steps": [
    {{
      "step_index": 1,
      "step_name": "Step Title",
      "tool_name": "tool_name",
      "tool_args": {{}},
      "rationale": "Why this step is needed"
    }}
  ]
}}
"""


def build_investigation_prompt(
    issue_type: str,
    target_file: str,
    error_output_or_symbol: str,
    code_context: str,
    references_found: int = 0,
) -> str:
    """Constructs prompt for investigating a test failure, lint violation, or dead code candidate."""
    return f"""INVESTIGATION TARGET:
Issue Type: {issue_type}
File Path: {target_file}
References Found across Codebase: {references_found}

ERROR LOG OR SYMBOL DETAILS:
{error_output_or_symbol}

SURROUNDING SOURCE CODE:
```
{code_context}
```

INSTRUCTIONS:
Analyze the issue carefully. Determine:
1. What is the root cause?
2. Is this finding certain or a false positive?
3. Is it SAFE to patch automatically without breaking external contracts or public APIs?
4. What is the recommended fix?

Output MUST be a single JSON object matching this schema:
{{
  "issue_title": "Concise title",
  "severity": "HIGH | MEDIUM | LOW | INFO",
  "category": "DEAD_CODE | TEST_FAILURE | LINT_ERROR | TYPE_ERROR | UNUSED_DEPENDENCY",
  "file_path": "{target_file}",
  "line_number": 1,
  "root_cause": "Detailed explanation",
  "evidence": "Concrete evidence (e.g. 0 callers found, stack trace line 42)",
  "confidence": "HIGH | MEDIUM | LOW",
  "is_safe_to_fix": true or false,
  "fix_approach": "Recommended patch method"
}}
"""


def build_fixer_prompt(
    file_path: str,
    issue_description: str,
    fix_approach: str,
    file_content: str,
) -> str:
    """Constructs prompt for CodeGemma to generate a minimal, surgical code patch."""
    return f"""TARGET FILE: {file_path}

ISSUE TO RESOLVE:
{issue_description}

PROPOSED FIX APPROACH:
{fix_approach}

CURRENT FILE CONTENT:
```
{file_content}
```

INSTRUCTIONS:
Provide a surgical, minimal replacement code block.
- `original_code_block` MUST match a real contiguous segment in the file content above character-for-character.
- `replacement_code_block` MUST contain the corrected code that resolves the issue cleanly.
- Do NOT rewrite unrelated functions or comments.

Output MUST be a single JSON object matching this schema:
{{
  "file_path": "{file_path}",
  "original_code_block": "exact code segment from original file to replace",
  "replacement_code_block": "new replacement code",
  "explanation": "Why this replacement resolves the issue safely",
  "confidence": "HIGH | MEDIUM | LOW"
}}
"""


def build_reporter_prompt(
    task_prompt: str,
    repo_meta: Dict[str, Any],
    steps_executed: List[Dict[str, Any]],
    findings: List[Dict[str, Any]],
    diffs_applied: List[Dict[str, Any]],
    test_results: Optional[Dict[str, Any]] = None,
    away_minutes: float = 25.0,
) -> str:
    """Constructs prompt to synthesize the final report and warm ElevenLabs voice briefing script."""
    findings_summary = f"Total findings: {len(findings)}"
    diffs_summary = f"Total fixes applied: {len(diffs_applied)}"
    test_summary_text = "Tests executed" if test_results else "No tests configured"
    if test_results:
        passed = test_results.get("passed", 0)
        failed = test_results.get("failed", 0)
        total = test_results.get("total", passed + failed)
        test_summary_text = f"{passed}/{total} tests passed ({failed} failed)"

    return f"""ORIGINAL TASK:
"{task_prompt}"

RUN SUMMARY:
- Time developer was away ('touching grass'): {int(away_minutes)} minutes
- Files inspected: {repo_meta.get('file_count', 0)}
- Test Results: {test_summary_text}
- Findings: {findings_summary}
- Fixes Applied on Branch: {diffs_summary}

FINDINGS DETAILS:
{findings[:10]}

INSTRUCTIONS:
1. Compute an objective Repository Health Score (0 to 100).
   - 90-100: All tests pass, clean code, no critical issues.
   - 70-89: Minor dead code or lint warnings, tests passing.
   - Below 70: Failing tests or serious issues.
2. Write a concise executive summary.
3. DRAFT THE 'TOUCH GRASS' WELCOME-BACK VOICE SCRIPT (for ElevenLabs voice synthesis).
   - Tone: Friendly, warm, celebratory, and concise (spoken in ~30 seconds).
   - Must acknowledge the time spent away (e.g. "Welcome back! While you spent {int(away_minutes)} minutes outside touching grass, I analyzed your repository...").
   - Highlight key test outcomes and verified fixes.

Output MUST be a single JSON object matching this schema:
{{
  "health_score": 92,
  "summary": "Executive summary paragraph",
  "files_analyzed_count": {repo_meta.get('file_count', 0)},
  "issues_found_count": {len(findings)},
  "safe_fixes_applied_count": {len(diffs_applied)},
  "test_summary": "{test_summary_text}",
  "key_findings": ["Bullet point 1", "Bullet point 2"],
  "voice_brief_script": "Welcome back! While you spent {int(away_minutes)} minutes outside touching grass..."
}}
"""
