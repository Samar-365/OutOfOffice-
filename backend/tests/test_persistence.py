"""Unit tests for SQLite Persistence & Re-hydration Engine (Submodule 6.2)."""

import uuid
from datetime import datetime
import pytest
from sqlalchemy import select

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


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


@pytest.mark.anyio
async def test_persistence_save_step_and_timeline():
    service = PersistenceService()
    job_id = f"test-persist-step-{uuid.uuid4().hex[:8]}"

    # Insert Job
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path="/test/repo",
            task_prompt="Audit test",
            mode=JobMode.AUDIT.value,
            status=JobStatus.RUNNING.value,
        )
        session.add(job)
        await session.commit()

    # Save multiple steps
    step1 = await service.save_step(
        job_id=job_id,
        step_index=0,
        step_name="Discovery",
        tool_name="repo_discovery",
        status=StepStatus.SUCCESS.value,
        stdout="Discovered 12 files",
        latency_ms=45.2,
    )
    assert step1.id is not None
    assert step1.step_name == "Discovery"

    step2 = await service.save_step(
        job_id=job_id,
        step_index=1,
        step_name="AST Analysis",
        tool_name="ast_parser",
        status=StepStatus.SUCCESS.value,
        stdout="Found 4 symbols",
        latency_ms=120.5,
    )
    assert step2.step_index == 1

    # Fetch timeline
    timeline = await service.get_job_timeline(job_id)
    assert len(timeline) == 2
    assert timeline[0]["step_name"] == "Discovery"
    assert timeline[0]["latency_ms"] == 45.2
    assert timeline[1]["step_name"] == "AST Analysis"


@pytest.mark.anyio
async def test_persistence_save_findings_and_summary():
    service = PersistenceService()
    job_id = f"test-persist-find-{uuid.uuid4().hex[:8]}"

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path="/test/repo",
            task_prompt="Finding test",
            mode=JobMode.AUDIT.value,
            status=JobStatus.RUNNING.value,
        )
        session.add(job)
        await session.commit()

    # Single finding
    f1 = await service.save_finding(
        job_id=job_id,
        file_path="src/unused.py",
        description="Unused function 'calculate_tax'",
        severity=FindingSeverity.HIGH.value,
        category=FindingCategory.DEAD_CODE.value,
        line_number=42,
        evidence="0 references found in workspace",
        confidence="HIGH",
        is_fixed=False,
    )
    assert f1.id is not None

    # Batch findings
    batch = [
        {
            "file_path": "src/utils.py",
            "description": "Lint warning: unused import",
            "severity": FindingSeverity.LOW.value,
            "category": FindingCategory.LINT_ERROR.value,
            "line_number": 3,
            "confidence": "HIGH",
            "is_fixed": True,
        },
        {
            "file_path": "tests/test_math.py",
            "description": "Failing test: assert 1 == 2",
            "severity": FindingSeverity.HIGH.value,
            "category": FindingCategory.TEST_FAILURE.value,
            "line_number": 15,
            "confidence": "HIGH",
            "is_fixed": True,
        },
    ]
    saved_batch = await service.save_findings_batch(job_id, batch)
    assert len(saved_batch) == 2

    # Summary
    summary = await service.get_findings_summary(job_id)
    assert summary["total"] == 3
    assert summary["fixed"] == 2
    assert summary["by_severity"]["HIGH"] == 2
    assert summary["by_severity"]["LOW"] == 1
    assert summary["by_category"]["DEAD_CODE"] == 1
    assert summary["by_category"]["TEST_FAILURE"] == 1


@pytest.mark.anyio
async def test_persistence_save_diff_and_audio():
    service = PersistenceService()
    job_id = f"test-persist-diff-{uuid.uuid4().hex[:8]}"

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path="/test/repo",
            task_prompt="Diff test",
            mode=JobMode.FIX.value,
            status=JobStatus.RUNNING.value,
        )
        session.add(job)
        await session.commit()

    diff_obj = await service.save_diff(
        job_id=job_id,
        file_path="app.py",
        diff_unified="--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-x = 1\n+x = 2",
        original_content="x = 1",
        patched_content="x = 2",
        status=DiffStatus.VALIDATED.value,
    )
    assert diff_obj.id is not None
    assert diff_obj.file_path == "app.py"

    audio_obj = await service.save_audio_briefing(
        job_id=job_id,
        audio_path="/artifacts/audio/briefing-123.mp3",
        script_text="Welcome back! I resolved 1 issue while you touched grass.",
        duration_seconds=12.4,
        provider="elevenlabs",
    )
    assert audio_obj.id is not None
    assert audio_obj.duration_seconds == 12.4


@pytest.mark.anyio
async def test_rehydrate_job_and_agent_state():
    service = PersistenceService()
    job_id = f"test-rehydrate-{uuid.uuid4().hex[:8]}"

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path="/projects/my-app",
            task_prompt="Autonomous refactoring",
            mode=JobMode.FIX.value,
            status=JobStatus.COMPLETED.value,
            health_score=94,
            final_report_markdown="# OutOfOffice Report\nAll tests passed.",
            base_branch="main",
            agent_branch="agent/outofoffice-12345",
            away_duration_seconds=145.8,
        )
        session.add(job)
        await session.commit()

    await service.save_step(job_id=job_id, step_index=0, step_name="Discovery", status="SUCCESS")
    await service.save_step(job_id=job_id, step_index=1, step_name="Tests", status="SUCCESS")
    await service.save_finding(
        job_id=job_id,
        file_path="src/index.ts",
        description="Dead export",
        severity="LOW",
        category="DEAD_CODE",
    )
    await service.save_diff(
        job_id=job_id,
        file_path="src/index.ts",
        diff_unified="@@ -1 +1 @@\n-const a = 1;\n+",
    )
    await service.save_audio_briefing(
        job_id=job_id,
        audio_path="/audio/test.mp3",
        script_text="All done.",
        duration_seconds=5.0,
    )

    # Rehydrate Job Dictionary
    job_data = await service.rehydrate_job(job_id)
    assert job_data is not None
    assert job_data["id"] == job_id
    assert job_data["health_score"] == 94
    assert job_data["total_steps"] == 2
    assert job_data["is_complete"] is True
    assert len(job_data["steps"]) == 2
    assert len(job_data["findings"]) == 1
    assert len(job_data["diffs"]) == 1
    assert job_data["audio_briefing"] is not None
    assert job_data["audio_briefing"]["script_text"] == "All done."

    # Rehydrate AgentState TypedDict
    agent_state = await service.rehydrate_agent_state(job_id)
    assert agent_state is not None
    assert agent_state["job_id"] == job_id
    assert agent_state["health_score"] == 94
    assert agent_state["current_step_idx"] == 2
    assert len(agent_state["findings"]) == 1
    assert len(agent_state["diffs"]) == 1
    assert agent_state["agent_branch"] == "agent/outofoffice-12345"


@pytest.mark.anyio
async def test_rehydrate_nonexistent_job():
    service = PersistenceService()
    job_data = await service.rehydrate_job("non-existent-job-id")
    assert job_data is None

    agent_state = await service.rehydrate_agent_state("non-existent-job-id")
    assert agent_state is None
