"""Unit tests for Touch Grass Away-Time Tracker & Metrics Service (Submodule 6.3)."""

import asyncio
from datetime import datetime, timedelta
import uuid
import pytest

from app.core.database import get_async_session_factory, init_db
from app.core.models import Job, JobMode, JobStatus
from app.services.timer_service import GrassTimerService, timer_service


@pytest.fixture(autouse=True)
def setup_database():
    init_db()


def test_timer_lifecycle_and_duration():
    service = GrassTimerService()
    job_id = f"test-job-timer-{uuid.uuid4().hex[:8]}"

    start_time = datetime.utcnow() - timedelta(seconds=125)
    service.start_timer(job_id, start_time=start_time)

    elapsed = service.get_elapsed_seconds(job_id)
    assert elapsed >= 124.0

    end_time = start_time + timedelta(seconds=130)
    duration = service.stop_timer(job_id, end_time=end_time)
    assert round(duration, 1) == 130.0

    # Stop non-existent timer
    assert service.stop_timer("unknown-job") == 0.0
    assert service.get_elapsed_seconds("unknown-job") == 0.0


def test_format_duration_hhmmss():
    assert GrassTimerService.format_duration_hhmmss(0) == "00:00:00"
    assert GrassTimerService.format_duration_hhmmss(45) == "00:00:45"
    assert GrassTimerService.format_duration_hhmmss(125) == "00:02:05"
    assert GrassTimerService.format_duration_hhmmss(3665) == "01:01:05"
    assert GrassTimerService.format_duration_hhmmss(86400) == "24:00:00"


def test_format_human_readable():
    assert "second" in GrassTimerService.format_human_readable(30)
    assert "2 minutes" in GrassTimerService.format_human_readable(120)
    assert "1 hour" in GrassTimerService.format_human_readable(3660)
    assert "away from keyboard" in GrassTimerService.format_human_readable(500)


def test_grass_badges_tiers():
    badge_quick = GrassTimerService.get_grass_badge(60)  # 1 min
    assert badge_quick["tier"] == "Sprout Quick-Step"
    assert "🌱" in badge_quick["icon"]

    badge_lawn = GrassTimerService.get_grass_badge(300)  # 5 min
    assert badge_lawn["tier"] == "Lawn Lounger"
    assert "🌿" in badge_lawn["icon"]

    badge_ranger = GrassTimerService.get_grass_badge(1200)  # 20 min
    assert badge_ranger["tier"] == "Park Ranger"
    assert "🌳" in badge_ranger["icon"]

    badge_forest = GrassTimerService.get_grass_badge(2400)  # 40 min
    assert badge_forest["tier"] == "Forest Hermit"
    assert "🌲" in badge_forest["icon"]

    badge_god = GrassTimerService.get_grass_badge(4000)  # 66 min
    assert badge_god["tier"] == "Transcendental Grass God"
    assert "🏔️" in badge_god["icon"]


def test_compute_grass_metrics():
    service = GrassTimerService()
    job_id = "test-metrics"
    metrics = service.compute_grass_metrics(job_id, duration_seconds=900)  # 15 minutes

    assert metrics["job_id"] == job_id
    assert metrics["duration_seconds"] == 900.0
    assert metrics["minutes_away"] == 15.0
    assert metrics["formatted_time"] == "00:15:00"
    assert metrics["estimated_steps"] == 1500
    assert metrics["badge"]["tier"] == "Park Ranger"
    assert "15 minutes" in metrics["human_readable"]


@pytest.mark.anyio
async def test_get_all_time_stats():
    session_factory = get_async_session_factory()
    job_id_1 = f"stats-1-{uuid.uuid4().hex[:6]}"
    job_id_2 = f"stats-2-{uuid.uuid4().hex[:6]}"

    async with session_factory() as session:
        j1 = Job(
            id=job_id_1,
            repo_path="/test",
            task_prompt="t1",
            mode=JobMode.AUDIT.value,
            status=JobStatus.COMPLETED.value,
            away_duration_seconds=300.0,
        )
        j2 = Job(
            id=job_id_2,
            repo_path="/test",
            task_prompt="t2",
            mode=JobMode.AUDIT.value,
            status=JobStatus.COMPLETED.value,
            away_duration_seconds=600.0,
        )
        session.add_all([j1, j2])
        await session.commit()

    stats = await timer_service.get_all_time_stats()
    assert stats["total_completed_jobs"] >= 2
    assert stats["total_grass_touched_seconds"] >= 900.0
    assert stats["total_grass_touched_minutes"] >= 15.0
    assert "formatted_total_time" in stats
    assert "all_time_badge" in stats
