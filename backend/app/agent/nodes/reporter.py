"""Final report synthesis, health score calculation, and voice brief generator node.

Computes an objective repository health score (0–100), generates executive markdown reports,
and drafts the 'Touch Grass' welcome-back voice script for ElevenLabs narration.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from app.agent.prompts import SYSTEM_PROMPT_AGENT_CORE, build_reporter_prompt
from app.agent.schemas import ReportOutput, parse_and_validate_json
from app.agent.state import AgentState
from app.core.events import EventType, event_bus
from app.integrations.ollama_client import ollama_client

logger = logging.getLogger("outofoffice.agent.reporter")


def calculate_health_score(
    test_results: Optional[Dict[str, Any]],
    findings: List[Dict[str, Any]],
    diffs: List[Dict[str, Any]],
) -> int:
    """Calculates deterministic Repository Health Score from 0 to 100."""
    score = 100

    # 1. Test results penalty
    if test_results:
        failed_count = test_results.get("failed", 0)
        score -= min(40, failed_count * 20)

    # 2. Findings penalties
    for f in findings:
        if f.get("is_fixed"):
            continue  # Don't penalize resolved issues

        sev = f.get("severity", "MEDIUM")
        if sev == "HIGH":
            score -= 15
        elif sev == "MEDIUM":
            score -= 4
        else:
            score -= 1

    # 3. Bonus for fixes applied
    score += min(15, len(diffs) * 5)

    return max(0, min(100, score))


def _generate_fallback_report(
    task_prompt: str,
    repo_meta: Dict[str, Any],
    findings: List[Dict[str, Any]],
    diffs: List[Dict[str, Any]],
    test_results: Optional[Dict[str, Any]],
    away_minutes: float,
) -> ReportOutput:
    """Generates a structured report deterministically if LLM is offline."""
    score = calculate_health_score(test_results, findings, diffs)
    file_count = repo_meta.get("file_count", 0)
    passed_tests = test_results.get("passed", 0) if test_results else 0
    failed_tests = test_results.get("failed", 0) if test_results else 0
    total_tests = passed_tests + failed_tests

    test_summary = f"{passed_tests}/{total_tests} tests passed" if total_tests > 0 else "All checks verified"
    key_findings = [f.get("title", "") for f in findings[:5]]

    mins_display = max(1, int(away_minutes))
    voice_script = (
        f"Welcome back! While you spent {mins_display} minutes outside touching grass, "
        f"OutOfOffice AI inspected {file_count} files in your repository, identified {len(findings)} issues, "
        f"applied {len(diffs)} validated safe fixes, and verified your build with a health score of {score} out of 100."
    )

    return ReportOutput(
        health_score=score,
        summary=f"Autonomous execution completed for task: '{task_prompt[:80]}'. Repository health evaluated at {score}/100.",
        files_analyzed_count=file_count,
        issues_found_count=len(findings),
        safe_fixes_applied_count=len(diffs),
        test_summary=test_summary,
        key_findings=key_findings,
        voice_brief_script=voice_script,
    )


async def reporter_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node synthesizing the final report and voice briefing."""
    job_id = state.get("job_id", "")
    task_prompt = state.get("task_prompt", "")
    repo_meta = state.get("repo_meta", {})
    findings = state.get("findings", [])
    diffs = state.get("diffs", [])
    test_results = state.get("post_fix_test_results") or state.get("test_results")
    model_name = state.get("model_name", "gemma2:9b")

    start_ts = state.get("away_start_timestamp", time.time())
    away_minutes = round((time.time() - start_ts) / 60.0, 1)

    logger.info(f"[{job_id}] Reporter node synthesizing final artifacts (Away duration: {away_minutes} mins).")

    report_output: ReportOutput

    if ollama_client.is_running():
        try:
            prompt = build_reporter_prompt(
                task_prompt=task_prompt,
                repo_meta=repo_meta,
                steps_executed=state.get("tool_history", []),
                findings=findings,
                diffs_applied=diffs,
                test_results=test_results,
                away_minutes=away_minutes,
            )
            raw_resp = await ollama_client.generate_async(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPT_AGENT_CORE,
                model=model_name,
                format_json=True,
            )
            report_output = parse_and_validate_json(raw_resp, ReportOutput)
        except Exception as e:
            logger.warning(f"[{job_id}] LLM report synthesis failed ({e}); using deterministic fallback.")
            report_output = _generate_fallback_report(task_prompt, repo_meta, findings, diffs, test_results, away_minutes)
    else:
        report_output = _generate_fallback_report(task_prompt, repo_meta, findings, diffs, test_results, away_minutes)

    # Format markdown report
    if report_output.key_findings:
        findings_bullets = "\n".join(f"- {kf}" for kf in report_output.key_findings)
    else:
        findings_bullets = "- No blocking issues detected."

    markdown_report = f"""# 🌳 OutOfOffice AI — Execution Report
**Repository:** `{repo_meta.get('repo_name', 'Local Codebase')}`  
**Task:** *"{task_prompt}"*  
**Repository Health Score:** **{report_output.health_score} / 100**  
**Away Time ('Grass Touched'):** {int(away_minutes)} minutes  

---

### Executive Summary
{report_output.summary}

### Key Metrics
* **Files Analyzed:** {report_output.files_analyzed_count}
* **Issues Discovered:** {report_output.issues_found_count}
* **Safe Fixes Applied:** {report_output.safe_fixes_applied_count}
* **Test Suite Status:** {report_output.test_summary}

### Key Findings
{findings_bullets}

---
*Generated autonomously by OutOfOffice AI with Google Gemma 2 & local-first inference.*
"""

    # Emit job completed event
    await event_bus.emit(
        EventType.JOB_COMPLETED,
        job_id=job_id,
        data={
            "health_score": report_output.health_score,
            "away_minutes": away_minutes,
            "summary": report_output.summary,
            "voice_brief_script": report_output.voice_brief_script,
        },
    )

    return {
        "health_score": report_output.health_score,
        "final_report_markdown": markdown_report,
        "voice_brief_script": report_output.voice_brief_script,
        "away_duration_minutes": away_minutes,
        "status": "COMPLETED",
        "logs": state.get("logs", []) + [f"Final report generated with Health Score: {report_output.health_score}/100."],
    }
