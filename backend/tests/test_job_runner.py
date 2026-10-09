"""Unit and integration tests for Asynchronous JobRunner orchestrator."""

import asyncio
import uuid
from datetime import datetime
import subprocess
from pathlib import Path
import pytest
from sqlalchemy import select

from app.core.database import get_async_session_factory, init_db
from app.core.models import Job, JobMode, JobStatus, JobStep
from app.services.job_runner import JobRunner, job_runner


def _init_test_git_repo(repo_dir: Path):
    subprocess.run(["git", "init", "-b", "main"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Test Runner"], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@runner.local"], cwd=str(repo_dir), capture_output=True, check=True)
    (repo_dir / "main.py").write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    (repo_dir / "requirements.txt").write_text("pytest>=7.0.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=str(repo_dir), capture_output=True, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(repo_dir), capture_output=True, check=True)


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


@pytest.mark.anyio
async def test_job_runner_start_and_complete_lifecycle(tmp_path):
    _init_test_git_repo(tmp_path)
    job_id = f"test-jr-{uuid.uuid4().hex[:8]}"

    # Pre-create job in database as API would
    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path=str(tmp_path),
            task_prompt="Audit codebase and run tests",
            mode=JobMode.AUDIT.value,
            status=JobStatus.QUEUED.value,
        )
        session.add(job)
        await session.commit()

    runner = JobRunner()
    task = await runner.start_job(
        job_id=job_id,
        repo_path=str(tmp_path),
        task_prompt="Audit codebase and run tests",
        mode="AUDIT",
    )

    assert runner.is_running(job_id) is True
    assert job_id in runner.get_running_job_ids()

    # Wait for completion
    final_state = await runner.wait_for_job(job_id, timeout=30.0)
    assert final_state is not None
    assert final_state["job_id"] == job_id
    assert runner.is_running(job_id) is False

    # Verify SQLite Persistence
    async with session_factory() as session:
        stmt = select(Job).filter(Job.id == job_id)
        res = await session.execute(stmt)
        db_job = res.scalar_one_or_none()

        assert db_job is not None
        assert db_job.status == JobStatus.COMPLETED.value
        assert db_job.started_at is not None
        assert db_job.finished_at is not None
        assert db_job.away_duration_seconds is not None
        assert db_job.away_duration_seconds >= 0
        assert db_job.health_score is not None
        assert db_job.final_report_markdown is not None

        # Verify steps recorded
        stmt_steps = select(JobStep).filter(JobStep.job_id == job_id)
        res_steps = await session.execute(stmt_steps)
        steps = res_steps.scalars().all()
        assert len(steps) >= 4


@pytest.mark.anyio
async def test_job_runner_cancel_job(tmp_path):
    _init_test_git_repo(tmp_path)
    job_id = f"test-cancel-{uuid.uuid4().hex[:8]}"

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path=str(tmp_path),
            task_prompt="Long audit prompt",
            mode=JobMode.AUDIT.value,
            status=JobStatus.QUEUED.value,
        )
        session.add(job)
        await session.commit()

    runner = JobRunner()
    await runner.start_job(
        job_id=job_id,
        repo_path=str(tmp_path),
        task_prompt="Long audit prompt",
        mode="AUDIT",
    )

    # Cancel immediately
    cancelled = await runner.cancel_job(job_id)
    assert cancelled is True

    # Give task a moment to process cancellation
    await asyncio.sleep(0.1)

    assert runner.is_running(job_id) is False

    async with session_factory() as session:
        stmt = select(Job).filter(Job.id == job_id)
        res = await session.execute(stmt)
        db_job = res.scalar_one_or_none()
        assert db_job.status == JobStatus.CANCELLED.value


@pytest.mark.anyio
async def test_job_runner_stop_all(tmp_path):
    _init_test_git_repo(tmp_path)
    job_ids = [f"job-multi-1-{uuid.uuid4().hex[:6]}", f"job-multi-2-{uuid.uuid4().hex[:6]}"]

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        for jid in job_ids:
            job = Job(
                id=jid,
                repo_path=str(tmp_path),
                task_prompt="Stop all test",
                mode=JobMode.AUDIT.value,
                status=JobStatus.QUEUED.value,
            )
            session.add(job)
        await session.commit()

    runner = JobRunner()
    for jid in job_ids:
        await runner.start_job(
            job_id=jid,
            repo_path=str(tmp_path),
            task_prompt="Stop all test",
            mode="AUDIT",
        )

    assert len(runner.get_running_job_ids()) == 2
    await runner.stop_all_jobs()
    await asyncio.sleep(0.1)
    assert len(runner.get_running_job_ids()) == 0


@pytest.mark.anyio
async def test_job_runner_failure_recovery(tmp_path, monkeypatch):
    job_id = f"test-fail-{uuid.uuid4().hex[:8]}"

    session_factory = get_async_session_factory()
    async with session_factory() as session:
        job = Job(
            id=job_id,
            repo_path=str(tmp_path),
            task_prompt="Fail test",
            mode=JobMode.AUDIT.value,
            status=JobStatus.QUEUED.value,
        )
        session.add(job)
        await session.commit()

    runner = JobRunner()

    # Monkeypatch agent_workflow.execute to raise an unexpected error
    async def mock_fail_execute(*args, **kwargs):
        raise RuntimeError("Simulated crash in LangGraph engine")

    from app.agent.graph import agent_workflow
    monkeypatch.setattr(agent_workflow, "execute", mock_fail_execute)

    await runner.start_job(
        job_id=job_id,
        repo_path=str(tmp_path),
        task_prompt="Fail test",
        mode="AUDIT",
    )

    final_state = await runner.wait_for_job(job_id, timeout=5.0)
    assert final_state["status"] == "FAILED"

    async with session_factory() as session:
        stmt = select(Job).filter(Job.id == job_id)
        res = await session.execute(stmt)
        db_job = res.scalar_one_or_none()
        assert db_job.status == JobStatus.FAILED.value
        assert "Simulated crash" in db_job.error_message
