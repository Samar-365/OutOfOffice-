"""Root-cause investigation node for the LangGraph agent workflow.

Analyzes test failure stack traces, dead-code candidates, and lint issues using Gemma 2
to diagnose root causes, assess confidence, and flag safe fix opportunities.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agent.prompts import SYSTEM_PROMPT_AGENT_CORE, build_investigation_prompt
from app.agent.schemas import InvestigationOutput, parse_and_validate_json
from app.agent.state import AgentState
from app.core.events import EventType, event_bus
from app.integrations.ollama_client import ollama_client

logger = logging.getLogger("outofoffice.agent.investigator")


def _read_code_snippet(repo_path: Path, file_rel_path: str, center_line: Optional[int] = 1, context_lines: int = 15) -> str:
    """Reads lines of source code around a target line number."""
    target_file = (repo_path / file_rel_path).resolve()
    if not target_file.exists() or not target_file.is_file():
        return ""
    try:
        lines = target_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        start = max(0, (center_line or 1) - context_lines // 2 - 1)
        end = min(len(lines), start + context_lines)
        return "\n".join(f"{i+1}: {lines[i]}" for i in range(start, end))
    except Exception:
        return ""


async def investigator_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node that diagnoses root causes for all detected issues."""
    job_id = state.get("job_id", "")
    repo_path = Path(state.get("repo_path", "")).resolve()
    model_name = state.get("model_name", "gemma2:9b")

    findings: List[Dict[str, Any]] = list(state.get("findings", []))
    dead_code = state.get("dead_code_candidates", [])
    static_issues = state.get("static_issues", [])
    test_results = state.get("test_results", {})

    logger.info(f"[{job_id}] Investigator node running. Analyzing {len(dead_code)} dead-code items, {len(static_issues)} static issues.")

    # 1. Investigate Test Failures
    failing_tests = test_results.get("failing_tests", [])
    for fail in failing_tests[:5]:
        fail_file = fail.get("file", "")
        test_name = fail.get("test_name", "Unknown test")
        snippet = _read_code_snippet(repo_path, fail_file) if fail_file else ""

        finding_dict = {
            "title": f"Failing Test: {test_name}",
            "severity": "HIGH",
            "category": "TEST_FAILURE",
            "file_path": fail_file,
            "line_number": None,
            "root_cause": f"Test '{test_name}' failed during execution.",
            "evidence": test_results.get("stderr_snippet") or "Non-zero exit code during test run",
            "confidence": "HIGH",
            "is_safe_to_fix": False,
            "fix_approach": "Investigate assertion failure or test mock configuration",
        }

        # Try LLM root cause analysis if code is available
        if snippet and ollama_client.is_running():
            try:
                prompt = build_investigation_prompt(
                    issue_type="TEST_FAILURE",
                    target_file=fail_file,
                    error_output_or_symbol=f"Test failure: {test_name}",
                    code_context=snippet,
                    references_found=1,
                )
                raw_resp = await ollama_client.generate_async(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT_AGENT_CORE,
                    model=model_name,
                    format_json=True,
                )
                parsed = parse_and_validate_json(raw_resp, InvestigationOutput)
                finding_dict["root_cause"] = parsed.root_cause
                finding_dict["evidence"] = parsed.evidence
                finding_dict["is_safe_to_fix"] = parsed.is_safe_to_fix
                finding_dict["fix_approach"] = parsed.fix_approach
            except Exception as e:
                logger.debug(f"LLM investigation skipped for {fail_file}: {e}")

        findings.append(finding_dict)
        await event_bus.emit(EventType.FINDING_DETECTED, job_id=job_id, data=finding_dict)

    # 2. Investigate Dead Code Candidates
    for candidate in dead_code[:10]:
        sym_name = candidate.get("symbol_name", "")
        file_path = candidate.get("file_path", "")
        line_num = candidate.get("line_start", 1)

        finding_dict = {
            "title": f"Unused Declaration: {sym_name}()",
            "severity": "MEDIUM",
            "category": "DEAD_CODE",
            "file_path": file_path,
            "line_number": line_num,
            "root_cause": f"Symbol '{sym_name}' is declared in {file_path} but has 0 references across the repository.",
            "evidence": candidate.get("evidence", "0 callers in symbol reference scan"),
            "confidence": candidate.get("confidence", "HIGH"),
            "is_safe_to_fix": True,
            "fix_approach": f"Prune unused declaration '{sym_name}' from {file_path}",
        }
        findings.append(finding_dict)
        await event_bus.emit(EventType.FINDING_DETECTED, job_id=job_id, data=finding_dict)

    # 3. Investigate Static / Syntax Issues
    for static_issue in static_issues[:10]:
        file_path = static_issue.get("file_path", "")
        line_num = static_issue.get("line_number", 1)
        severity = static_issue.get("severity", "LOW")
        msg = static_issue.get("message", "")
        category = "SYNTAX_ERROR" if severity == "HIGH" else "LINT_ERROR"

        finding_dict = {
            "title": f"{category}: {msg[:60]}",
            "severity": severity,
            "category": category,
            "file_path": file_path,
            "line_number": line_num,
            "root_cause": msg,
            "evidence": f"Static analysis flag on line {line_num}",
            "confidence": "HIGH",
            "is_safe_to_fix": False,
            "fix_approach": "Review syntax or complete annotation action item",
        }
        findings.append(finding_dict)
        await event_bus.emit(EventType.FINDING_DETECTED, job_id=job_id, data=finding_dict)

    logger.info(f"[{job_id}] Investigation complete. Total findings assembled: {len(findings)}")

    return {
        "findings": findings,
        "logs": state.get("logs", []) + [f"Investigator analyzed issues: {len(findings)} findings compiled."],
    }
