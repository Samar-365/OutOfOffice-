"""Fix and validation cycle node for the LangGraph agent workflow.

Applies surgical code patches on an isolated Git branch in Fix Mode,
re-runs test suites immediately to prevent regressions, and rolls back failed patches.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from app.agent.prompts import SYSTEM_PROMPT_AGENT_CORE, build_fixer_prompt
from app.agent.schemas import PatchOutput, parse_and_validate_json
from app.agent.state import AgentState
from app.core.events import EventType, event_bus
from app.integrations.ollama_client import ollama_client
from app.tools.git_manager import GitManager
from app.tools.patcher import apply_surgical_patch, rollback_patch
from app.tools.test_runner import run_test_suite

logger = logging.getLogger("outofoffice.agent.fixer")


async def fixer_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node that synthesizes, applies, and validates surgical code patches in Fix Mode."""
    job_id = state.get("job_id", "")
    repo_path_str = state.get("repo_path", "")
    repo_path = Path(repo_path_str).resolve()
    mode = state.get("mode", "AUDIT")
    findings = list(state.get("findings", []))
    diffs: List[Dict[str, Any]] = list(state.get("diffs", []))
    model_name = state.get("model_name", "codegemma")

    # In AUDIT mode, skip any code mutations
    if mode != "FIX":
        logger.info(f"[{job_id}] Mode is AUDIT; skipping code modifications.")
        return {"diffs": []}

    logger.info(f"[{job_id}] Fixer node started in FIX mode. Evaluating {len(findings)} findings.")

    git_mgr = GitManager(repo_path_str)
    base_branch = state.get("base_branch") or git_mgr.get_current_branch()
    agent_branch = state.get("agent_branch")

    # 1. Ensure isolated agent branch exists
    if not agent_branch:
        ok, base_b, new_branch = git_mgr.create_isolated_branch()
        if ok:
            base_branch = base_b
            agent_branch = new_branch
            logger.info(f"[{job_id}] Checked out isolated branch: {agent_branch}")
        else:
            logger.error(f"[{job_id}] Could not create isolated Git branch. Aborting fixes.")
            return {"errors": state.get("errors", []) + ["Failed to create isolated Git branch"]}

    # Filter findings flagged as safe to fix
    safe_findings = [f for f in findings if f.get("is_safe_to_fix")]
    logger.info(f"[{job_id}] Found {len(safe_findings)} safe-fix candidates.")

    for finding in safe_findings[:3]:  # Limit to 3 safe fixes per autonomous run for safety
        file_path_rel = finding.get("file_path", "")
        desc = finding.get("title", "")
        approach = finding.get("fix_approach", "")
        target_file = (repo_path / file_path_rel).resolve()

        if not target_file.exists() or not target_file.is_file():
            continue

        try:
            file_content = target_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        patch_output: PatchOutput

        if ollama_client.is_running():
            try:
                prompt = build_fixer_prompt(
                    file_path=file_path_rel,
                    issue_description=desc,
                    fix_approach=approach,
                    file_content=file_content,
                )
                raw_resp = await ollama_client.generate_async(
                    prompt=prompt,
                    system_prompt=SYSTEM_PROMPT_AGENT_CORE,
                    model=model_name,
                    format_json=True,
                )
                patch_output = parse_and_validate_json(raw_resp, PatchOutput)
            except Exception as e:
                logger.warning(f"[{job_id}] CodeGemma patch synthesis failed for {file_path_rel}: {e}")
                continue
        else:
            logger.info(f"[{job_id}] Ollama offline; skipping LLM patch generation.")
            continue

        # Apply surgical patch
        patch_res = apply_surgical_patch(
            repo_path_str=repo_path_str,
            file_rel_path=file_path_rel,
            target_content=patch_output.original_code_block,
            replacement_content=patch_output.replacement_code_block,
            verify_syntax=True,
        )

        if not patch_res.success:
            logger.warning(f"[{job_id}] Patch rejected for {file_path_rel}: {patch_res.error}")
            continue

        # Immediately validate against test suite
        test_res = run_test_suite(repo_path_str, timeout=30)

        if test_res.is_success or test_res.failed == 0:
            # Commit patch on agent branch
            git_mgr.stage_and_commit(f"fix(agent): {desc} on {file_path_rel}")
            finding["is_fixed"] = True
            diff_entry = {
                "file_path": file_path_rel,
                "diff_unified": patch_res.diff_unified,
                "status": "VALIDATED",
                "explanation": patch_output.explanation,
            }
            diffs.append(diff_entry)
            await event_bus.emit(EventType.DIFF_PRODUCED, job_id=job_id, data=diff_entry)
            logger.info(f"[{job_id}] Successfully applied and validated fix on {file_path_rel}!")
        else:
            # Regression detected; rollback patch
            logger.warning(f"[{job_id}] Test regression detected post-patch on {file_path_rel}. Rolling back...")
            rollback_patch(repo_path_str, file_path_rel, patch_res.original_content or "")
            finding["is_fixed"] = False

    # Get final post-fix test results
    final_test_res = run_test_suite(repo_path_str, timeout=30).to_dict()

    return {
        "base_branch": base_branch,
        "agent_branch": agent_branch,
        "findings": findings,
        "diffs": diffs,
        "post_fix_test_results": final_test_res,
        "logs": state.get("logs", []) + [f"Fixer cycle finished: {len(diffs)} validated diffs applied on {agent_branch}."],
    }
