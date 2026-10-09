"""
Headless Recovery & Persistence Verification Suite (Submodule 9.2).
Tests client disconnection, background execution durability, and zero-loss state rehydration.
"""

import os
import uuid
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
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
from app.services.persistence import PersistenceService, persistence_service
from app.services.timer_service import GrassTimerService, timer_service
from app.services.job_runner import JobRunner, job_runner
from app.integrations.sentry_telemetry import SentryTelemetryManager

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    yield


@pytest.mark.anyio
async def test_headless_browser_disconnect_and_full_rehydration():
    """
    Simulates a developer launching a job, immediately closing their laptop / browser
    for 30 minutes, and re-opening to verify 100% state rehydration.
    """
    p_service = PersistenceService()
    t_service = GrassTimerService()
    sentry = SentryTelemetryManager()

    job_id = f"headless-recovery-{uuid.uuid4().hex[:8]}"

    # Phase 1: User launches job and starts timer
    start_time = datetime.utcnow() - timedelta(minutes=28)
    t_service.start_timer(job_id, start_time=start_time)

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path=str(ROOT_DIR),
            task_prompt="Find and prune dead code across repository",
            mode=JobMode.FIX,
            status=JobStatus.RUNNING,
            base_branch="main",
            agent_branch=f"agent/outofoffice-{job_id[:8]}",
            started_at=start_time,
        )
        session.add(job)
        await session.commit()

    # Phase 2: User CLOSES browser (no active WebSocket / no HTTP requests).
    # Background worker independently records multiple execution steps and findings in SQLite:
    steps_data = [
        ("AST Discovery & Indexing", "repo_discovery", "Indexed 114 source files", 340),
        ("Dead Code Reference Search", "search_engine", "Scanned symbol references with ripgrep", 820),
        ("Test Suite Execution", "test_runner", "pytest run on isolated branch: 2 failures found", 1450),
        ("AST Fixer & Surgical Patch", "patcher", "Synthesized clean patch for failing assertion", 410),
        ("Test Re-verification", "test_runner", "pytest run: 14/14 tests green", 1210),
    ]

    for idx, (name, tool, stdout, latency) in enumerate(steps_data):
        await p_service.save_step(
            job_id=job_id,
            step_index=idx,
            step_name=name,
            tool_name=tool,
            status=StepStatus.SUCCESS,
            stdout=stdout,
            latency_ms=latency,
        )

    # Record finding & diff
    await p_service.save_finding(
        job_id=job_id,
        severity=FindingSeverity.HIGH,
        category=FindingCategory.TEST_FAILURE,
        file_path="app/calculator.py",
        description="Failing subtraction assertion resolved",
        line_number=8,
        confidence="HIGH",
        is_fixed=True,
    )

    await p_service.save_diff(
        job_id=job_id,
        file_path="app/calculator.py",
        diff_unified="--- a/app/calculator.py\n+++ b/app/calculator.py\n@@ -8,1 +8,1 @@\n-    return a + b\n+    return a - b",
        status=DiffStatus.VALIDATED,
    )

    # Sentry trace recorded in background
    async with sentry.trace_agent_job(job_id=job_id, repo_path=str(ROOT_DIR), mode="FIX"):
        async with sentry.trace_step(job_id=job_id, step_name="Autonomous Execution", step_index=0):
            await asyncio.sleep(0.005)

    # Job completes in background while user is away
    finished_time = datetime.utcnow()
    await p_service.update_job_status(
        job_id=job_id,
        status=JobStatus.COMPLETED,
        health_score=96,
        final_report_markdown="# OutOfOffice Mission Complete\nAll tests green.",
        finished_at=finished_time,
    )

    # Phase 3: Developer returns 28 minutes later, reopens browser!
    # Rehydration engine reconstructs complete timeline from SQLite:
    rehydrated = await p_service.rehydrate_job(job_id)
    assert rehydrated is not None
    assert rehydrated["id"] == job_id
    assert rehydrated["status"] == JobStatus.COMPLETED.value
    assert rehydrated["health_score"] == 96
    assert rehydrated["agent_branch"] == f"agent/outofoffice-{job_id[:8]}"

    # Verify all 5 chronological steps are fully intact
    assert len(rehydrated["steps"]) == 5
    assert rehydrated["steps"][0]["step_name"] == "AST Discovery & Indexing"
    assert rehydrated["steps"][4]["step_name"] == "Test Re-verification"
    assert "14/14 tests green" in rehydrated["steps"][4]["stdout"]

    # Verify findings and diffs rehydrated
    assert len(rehydrated["findings"]) == 1
    assert rehydrated["findings"][0]["is_fixed"] is True
    assert len(rehydrated["diffs"]) == 1
    assert "return a - b" in rehydrated["diffs"][0]["diff_unified"]

    # Verify Grass Away Metrics include full offline elapsed time
    duration = t_service.stop_timer(job_id, end_time=finished_time)
    metrics = t_service.compute_grass_metrics(job_id, duration_seconds=duration)
    assert metrics["minutes_away"] >= 27
    assert metrics["badge"]["tier"] in ("Park Ranger", "Forest Hermit")

    # Verify Sentry traces are preserved
    spans = sentry.get_job_spans(job_id)
    assert len(spans) == 2


@pytest.mark.anyio
async def test_headless_recovery_on_failed_job():
    """
    Verifies that if a job encounters a failure while the developer is away,
    rehydration cleanly captures the failure error message and exact step.
    """
    p_service = PersistenceService()
    job_id = f"headless-fail-{uuid.uuid4().hex[:8]}"

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path=str(ROOT_DIR),
            task_prompt="Run build verification",
            mode=JobMode.AUDIT,
            status=JobStatus.RUNNING,
        )
        session.add(job)
        await session.commit()

    # Step 1 succeeded
    await p_service.save_step(
        job_id=job_id,
        step_index=0,
        step_name="Discovery",
        tool_name="repo_discovery",
        status=StepStatus.SUCCESS,
        stdout="Indexed files",
        latency_ms=100,
    )

    # Step 2 failed
    await p_service.save_step(
        job_id=job_id,
        step_index=1,
        step_name="Compilation",
        tool_name="test_runner",
        status=StepStatus.FAILED,
        stderr="Syntax error on line 42: unexpected token",
        latency_ms=250,
    )

    await p_service.update_job_status(
        job_id=job_id,
        status=JobStatus.FAILED,
        error_message="Compilation failed on line 42",
    )

    # Developer reopens browser
    rehydrated = await p_service.rehydrate_job(job_id)
    assert rehydrated is not None
    assert rehydrated["status"] == JobStatus.FAILED.value
    assert rehydrated["error_message"] == "Compilation failed on line 42"
    assert len(rehydrated["steps"]) == 2
    assert rehydrated["steps"][1]["status"] == StepStatus.FAILED.value
    assert "Syntax error" in rehydrated["steps"][1]["stderr"]
