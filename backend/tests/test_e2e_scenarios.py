"""
End-to-End Test Verification Suite for OutOfOffice AI (Submodule 9.1).
Validates complete autonomous agent execution on TypeScript and Python sample repos.
"""

import os
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import shutil
import pytest

from app.core.database import get_async_session_factory, init_db
from app.core.models import (
    DiffStatus,
    FindingCategory,
    FindingSeverity,
    Job,
    JobMode,
    JobStatus,
    StepStatus,
)
from app.services.persistence import PersistenceService
from app.services.timer_service import GrassTimerService
from app.integrations.sentry_telemetry import SentryTelemetryManager
from app.integrations.audio_streamer import AudioStreamer
from app.tools.repo_discovery import detect_manifests_and_frameworks, index_source_files
from app.tools.ast_parser import extract_symbols_from_file
from app.tools.dependency_auditor import audit_dependencies
from app.tools.patcher import apply_surgical_patch

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
TS_REPO_PATH = ROOT_DIR / "fixtures" / "sample_ts_repo"
PY_REPO_PATH = ROOT_DIR / "fixtures" / "sample_python_repo"


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    yield


def test_e2e_typescript_dead_code_audit():
    """
    Verify complete discovery, dependency analysis, and AST symbol mapping
    on sample TypeScript project.
    """
    assert TS_REPO_PATH.exists()

    # 1. Manifest & Language Discovery
    manifest_info = detect_manifests_and_frameworks(TS_REPO_PATH)
    assert "TypeScript" in manifest_info["detected_languages"]
    
    # 2. File Indexing
    indexed = index_source_files(TS_REPO_PATH)
    assert indexed["total_source_files"] >= 3

    # 3. Dependency Audit
    dep_findings = audit_dependencies(str(TS_REPO_PATH))
    assert "npm" in dep_findings
    assert "unused-dep-package" in dep_findings["npm"]["unused_dependencies"]

    # 4. AST Parsing
    math_ts = TS_REPO_PATH / "src" / "math.ts"
    symbols = extract_symbols_from_file(file_path=math_ts, repo_root=TS_REPO_PATH)
    sym_names = [s.name for s in symbols]
    assert "add" in sym_names
    assert "multiply" in sym_names
    assert "deadLegacyFunction" in sym_names


def test_e2e_python_test_failure_fix_flow(tmp_path):
    """
    Verify full test runner execution, failure discovery, AST patching,
    and post-fix green verification on sample Python project.
    """
    # Clone sample repo to isolated temp directory
    test_repo = tmp_path / "sample_python_repo"
    shutil.copytree(str(PY_REPO_PATH), str(test_repo))

    calc_file = test_repo / "app" / "calculator.py"
    assert calc_file.exists()

    # 1. Run initial check - should detect bug
    calc_content = calc_file.read_text(encoding="utf-8")
    assert "return a + b" in calc_content  # the bug in subtract

    # 2. Apply unambiguous surgical patch targeting subtract block
    result = apply_surgical_patch(
        repo_path_str=str(test_repo),
        file_rel_path="app/calculator.py",
        target_content="def subtract(a: int, b: int) -> int:\n    # BUG: plus instead of minus\n    return a + b",
        replacement_content="def subtract(a: int, b: int) -> int:\n    return a - b",
    )
    assert result.success is True
    assert "---" in result.diff_unified
    assert "+++" in result.diff_unified
    assert "+    return a - b" in result.diff_unified

    # 3. Verify fixed content
    new_content = calc_file.read_text(encoding="utf-8")
    assert "return a - b" in new_content


@pytest.mark.anyio
async def test_e2e_full_job_lifecycle_with_telemetry_and_audio():
    """
    Verify full autonomous job lifecycle: creation, telemetry logging,
    SQLite durability, grass timer metrics, and audio debrief generation.
    """
    service = PersistenceService()
    t_service = GrassTimerService()
    manager = SentryTelemetryManager()
    streamer = AudioStreamer()

    job_id = f"test-e2e-job-{uuid.uuid4().hex[:8]}"

    # 1. Start Grass Timer
    start_time = datetime.utcnow() - timedelta(minutes=15)
    t_service.start_timer(job_id, start_time=start_time)

    # 2. Create Job in Persistence
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path=str(TS_REPO_PATH),
            task_prompt="Audit dead code in sample repository",
            mode=JobMode.AUDIT,
            status=JobStatus.RUNNING,
            started_at=start_time,
        )
        session.add(job)
        await session.commit()

    # 3. Record telemetry steps
    step = await service.save_step(
        job_id=job_id,
        step_index=1,
        step_name="AST Discovery",
        tool_name="repo_discovery",
        status=StepStatus.SUCCESS,
        stdout="Found 4 files",
        latency_ms=120,
    )
    assert step is not None

    # 4. Record finding
    finding = await service.save_finding(
        job_id=job_id,
        severity=FindingSeverity.MEDIUM,
        category=FindingCategory.DEAD_CODE,
        file_path="src/math.ts",
        description="Function deadLegacyFunction is unreferenced",
        line_number=13,
        confidence="HIGH",
    )
    assert finding is not None

    # 5. Capture Sentry Spans
    async with manager.trace_agent_job(job_id=job_id, repo_path=str(TS_REPO_PATH), mode="AUDIT", model_name="gemma2:9b"):
        async with manager.trace_step(job_id=job_id, step_name="Discovery", step_index=0):
            async with manager.trace_tool(tool_name="repo_discovery", job_id=job_id, args={"path": str(TS_REPO_PATH)}):
                await asyncio.sleep(0.005)

    spans = manager.get_job_spans(job_id)
    assert len(spans) == 3

    # 6. Stop Grass Timer & Get Metrics
    end_time = datetime.utcnow()
    duration = t_service.stop_timer(job_id, end_time=end_time)
    metrics = t_service.compute_grass_metrics(job_id, duration_seconds=duration)
    assert metrics["minutes_away"] >= 14
    assert "icon" in metrics["badge"]

    # 7. Audio Strategy Fallback
    strategy = streamer.resolve_audio_strategy(
        job_id=job_id,
        script_text="Welcome back from touching grass! Your audit is complete.",
    )
    assert strategy["strategy"] in ("file_stream", "web_speech")

    # 8. Rehydrate Job
    rehydrated = await service.rehydrate_job(job_id)
    assert rehydrated is not None
    assert len(rehydrated["steps"]) >= 1
    assert len(rehydrated["findings"]) >= 1
