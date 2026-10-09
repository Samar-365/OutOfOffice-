"""Job management, execution queries, and real-time streaming API routes."""

import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.schemas import JobCreateRequest, JobResponse
from app.core.config import settings
from app.core.database import get_async_db
from app.core.events import EventType, event_bus
from app.integrations.ollama_client import ollama_client
from app.integrations.sentry_telemetry import sentry_tracer
from app.services.job_runner import job_runner
from app.services.persistence import persistence_service
from app.services.timer_service import timer_service
from app.core.models import (
    AudioBriefing,
    CodeDiff,
    Finding,
    Job,
    JobMode,
    JobStatus,
    JobStep,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/models/status")
async def get_models_status():
    """Returns local Ollama inference status and installed models."""
    is_running = await ollama_client.is_running_async()
    installed = ollama_client.list_local_models() if is_running else []
    return {
        "ollama_running": is_running,
        "default_model": settings.DEFAULT_MODEL,
        "installed_models": installed,
        "has_default_model": any(settings.DEFAULT_MODEL in m for m in installed),
    }


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreateRequest, db: AsyncSession = Depends(get_async_db)):
    """Creates a new autonomous coding job in SQLite and registers it with the event bus."""
    clean_repo = payload.repo_path.strip()
    repo_path = Path(clean_repo).resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid repository directory: {clean_repo}",
        )

    mode_val = payload.mode.upper()
    if mode_val not in [JobMode.AUDIT.value, JobMode.FIX.value]:
        mode_val = JobMode.AUDIT.value

    job = Job(
        repo_path=str(repo_path),
        task_prompt=payload.task_prompt.strip(),
        mode=mode_val,
        status=JobStatus.QUEUED.value,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Emit event to global listeners
    await event_bus.emit(
        EventType.JOB_CREATED,
        job_id=job.id,
        data={
            "id": job.id,
            "repo_path": job.repo_path,
            "task_prompt": job.task_prompt,
            "mode": job.mode,
            "status": job.status,
            "created_at": job.created_at.isoformat(),
        },
    )

    # Launch background job execution decoupled from HTTP request lifecycle
    await job_runner.start_job(
        job_id=job.id,
        repo_path=job.repo_path,
        task_prompt=job.task_prompt,
        mode=job.mode,
    )

    return JobResponse(**job.to_dict())


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_async_db),
):
    """Lists recent jobs ordered by creation timestamp descending."""
    query = (
        select(Job)
        .options(selectinload(Job.steps), selectinload(Job.findings), selectinload(Job.diffs), selectinload(Job.audio_briefing))
        .order_by(desc(Job.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    jobs = result.scalars().all()
    return [JobResponse(**j.to_dict()) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, db: AsyncSession = Depends(get_async_db)):
    """Retrieves comprehensive details of a specific job including steps, findings, and diffs."""
    query = (
        select(Job)
        .options(
            selectinload(Job.steps),
            selectinload(Job.findings),
            selectinload(Job.diffs),
            selectinload(Job.audio_briefing),
        )
        .filter(Job.id == job_id)
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job not found: {job_id}")

    job_data = job.to_dict()
    job_data["steps"] = [s.to_dict() for s in job.steps]
    job_data["findings"] = [f.to_dict() for f in job.findings]
    job_data["diffs"] = [d.to_dict() for d in job.diffs]
    if job.audio_briefing:
        job_data["audio_briefing"] = job.audio_briefing.to_dict()

    return JobResponse(**job_data)


@router.get("/{job_id}/diff")
async def get_job_diff(job_id: str, db: AsyncSession = Depends(get_async_db)):
    """Returns all unified diffs produced for the job."""
    query = select(CodeDiff).filter(CodeDiff.job_id == job_id).order_by(CodeDiff.created_at)
    result = await db.execute(query)
    diffs = result.scalars().all()
    return {"job_id": job_id, "diffs": [d.to_dict() for d in diffs]}


@router.get("/{job_id}/audio")
async def get_job_audio(job_id: str, db: AsyncSession = Depends(get_async_db)):
    """Streams or downloads the generated ElevenLabs welcome-back audio briefing."""
    query = select(AudioBriefing).filter(AudioBriefing.job_id == job_id)
    result = await db.execute(query)
    briefing = result.scalar_one_or_none()

    if not briefing or not briefing.audio_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No audio briefing available for this job.")

    audio_path = Path(briefing.audio_path)
    if not audio_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found on disk.")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/mpeg",
        filename=f"briefing-{job_id}.mp3",
    )


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(job_id: str, db: AsyncSession = Depends(get_async_db)):
    """Cancels a queued or running job."""
    query = select(Job).filter(Job.id == job_id)
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job not found: {job_id}")

    if job.status in [JobStatus.RUNNING.value, JobStatus.QUEUED.value]:
        await job_runner.cancel_job(job_id)
        job.status = JobStatus.CANCELLED.value
        await db.commit()
        await db.refresh(job)
        await event_bus.emit(EventType.JOB_CANCELLED, job_id=job.id, data={"status": job.status})

    return JobResponse(**job.to_dict())


@router.get("/{job_id}/rehydrate")
async def rehydrate_job_state(job_id: str):
    """Rehydrates complete historical timeline and durable state for a returning user."""
    data = await persistence_service.rehydrate_job(job_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job not found: {job_id}")
    return data


@router.get("/{job_id}/timeline")
async def get_job_timeline(job_id: str):
    """Returns chronologically ordered execution steps for waterfall timeline visualizers."""
    timeline = await persistence_service.get_job_timeline(job_id)
    return {"job_id": job_id, "timeline": timeline}


@router.get("/community/grass-stats")
async def get_community_grass_stats():
    """Aggregates all-time 'Touch Grass' metrics across all completed jobs."""
    stats = await timer_service.get_all_time_stats()
    return stats


@router.get("/{job_id}/grass-metrics")
async def get_job_grass_metrics(job_id: str, db: AsyncSession = Depends(get_async_db)):
    """Computes gamified outdoor away metrics and badges for a specific job."""
    stmt = select(Job).filter(Job.id == job_id)
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job not found: {job_id}")

    metrics = timer_service.compute_grass_metrics(job_id, job.away_duration_seconds)
    return metrics


@router.get("/{job_id}/traces")
async def get_job_traces(job_id: str):
    """Returns Sentry agent tracing waterfall telemetry for latency and step analysis."""
    traces = sentry_tracer.export_waterfall(job_id)
    return traces



