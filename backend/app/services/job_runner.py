"""Asynchronous Job Orchestrator & Background Worker for OutOfOffice AI.

Manages decoupled background execution of the LangGraph autonomous agent workflow,
handles SQLite state persistence across job lifecycles, emits real-time telemetry
events, and tracks "Touch Grass" away-time durations.
"""

import asyncio
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import select

from app.agent.graph import agent_workflow
from app.agent.state import AgentState
from app.core.database import get_async_session_factory
from app.core.events import EventType, event_bus
from app.integrations.elevenlabs_brief import elevenlabs_generator
from app.core.models import (
    AudioBriefing,
    CodeDiff,
    DiffStatus,
    Finding,
    FindingCategory,
    FindingSeverity,
    Job,
    JobStatus,
    JobStep,
    StepStatus,
)

logger = logging.getLogger("outofoffice.services.job_runner")


class JobRunner:
    """Orchestrates background autonomous agent jobs independently of HTTP requests."""

    def __init__(self):
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_job(
        self,
        job_id: str,
        repo_path: str,
        task_prompt: str,
        mode: str = "AUDIT",
        model_name: Optional[str] = None,
    ) -> asyncio.Task:
        """Launches agent execution in a decoupled asynchronous background task."""
        async with self._lock:
            if job_id in self._running_tasks and not self._running_tasks[job_id].done():
                logger.warning(f"Job {job_id} is already running in background.")
                return self._running_tasks[job_id]

            task = asyncio.create_task(
                self._execute_job_lifecycle(
                    job_id=job_id,
                    repo_path=repo_path,
                    task_prompt=task_prompt,
                    mode=mode,
                    model_name=model_name,
                ),
                name=f"job-{job_id}",
            )
            self._running_tasks[job_id] = task

            def _cleanup(t: asyncio.Task):
                # Clean up finished task from dict
                if job_id in self._running_tasks and self._running_tasks[job_id] == t:
                    del self._running_tasks[job_id]

            task.add_done_callback(_cleanup)
            logger.info(f"Background task launched for job {job_id}.")
            return task

    async def cancel_job(self, job_id: str) -> bool:
        """Cancels a running background job task and updates its status in SQLite."""
        async with self._lock:
            task = self._running_tasks.get(job_id)
            if task and not task.done():
                logger.info(f"Cancelling background task for job {job_id}...")
                task.cancel()
                await self._mark_job_cancelled_in_db(job_id, datetime.utcnow())
                return True

        # If not actively in memory but in DB as QUEUED or RUNNING, update DB
        await self._mark_job_cancelled_in_db(job_id, datetime.utcnow())
        return False

    def is_running(self, job_id: str) -> bool:
        """Checks if a job task is currently active in memory."""
        task = self._running_tasks.get(job_id)
        return task is not None and not task.done()

    def get_running_job_ids(self) -> List[str]:
        """Returns list of currently active background job IDs."""
        return [job_id for job_id, task in self._running_tasks.items() if not task.done()]

    async def wait_for_job(self, job_id: str, timeout: Optional[float] = None) -> Optional[AgentState]:
        """Waits for a specific background job to finish and returns its final state."""
        task = self._running_tasks.get(job_id)
        if not task:
            return None
        if timeout:
            return await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        return await task

    async def stop_all_jobs(self) -> None:
        """Cancels all active background tasks gracefully on application shutdown."""
        async with self._lock:
            for job_id, task in list(self._running_tasks.items()):
                if not task.done():
                    logger.info(f"Stopping job task {job_id} for shutdown...")
                    task.cancel()
            self._running_tasks.clear()

    async def _execute_job_lifecycle(
        self,
        job_id: str,
        repo_path: str,
        task_prompt: str,
        mode: str = "AUDIT",
        model_name: Optional[str] = None,
    ) -> AgentState:
        """Executes the complete decoupled lifecycle for an autonomous job."""
        started_at = datetime.utcnow()
        logger.info(f"[{job_id}] Starting background execution lifecycle for '{repo_path}' ({mode}).")

        # 1. Update DB to RUNNING
        await self._update_job_status_db(job_id, JobStatus.RUNNING.value, started_at=started_at)
        await event_bus.emit(
            EventType.JOB_STARTED,
            job_id=job_id,
            data={
                "job_id": job_id,
                "repo_path": repo_path,
                "mode": mode,
                "task_prompt": task_prompt,
                "started_at": started_at.isoformat(),
            },
        )

        final_state: Optional[AgentState] = None
        try:
            # 2. Run LangGraph Workflow
            final_state = await agent_workflow.execute(
                job_id=job_id,
                repo_path=repo_path,
                task_prompt=task_prompt,
                mode=mode,
                model_name=model_name,
                on_step_update=self._handle_step_callback,
            )

            finished_at = datetime.utcnow()
            away_duration = (finished_at - started_at).total_seconds()
            final_state["away_duration_seconds"] = away_duration

            # 3. Persist final results to SQLite
            await self._persist_final_results(job_id, final_state, finished_at, away_duration)

            # 4. Emit completion event
            await event_bus.emit(
                EventType.JOB_COMPLETED,
                job_id=job_id,
                data={
                    "job_id": job_id,
                    "status": JobStatus.COMPLETED.value,
                    "health_score": final_state.get("health_score", 100),
                    "away_duration_seconds": away_duration,
                    "finished_at": finished_at.isoformat(),
                    "finding_count": len(final_state.get("findings", [])),
                    "diff_count": len(final_state.get("diffs", [])),
                },
            )
            logger.info(f"[{job_id}] Background job finished successfully. Away time: {away_duration:.1f}s.")
            return final_state

        except asyncio.CancelledError:
            finished_at = datetime.utcnow()
            away_duration = (finished_at - started_at).total_seconds()
            logger.warning(f"[{job_id}] Background job was cancelled.")
            await self._mark_job_cancelled_in_db(job_id, finished_at, away_duration)
            await event_bus.emit(
                EventType.JOB_CANCELLED,
                job_id=job_id,
                data={"job_id": job_id, "status": JobStatus.CANCELLED.value},
            )
            raise

        except Exception as e:
            finished_at = datetime.utcnow()
            away_duration = (finished_at - started_at).total_seconds()
            logger.error(f"[{job_id}] Background job failed with exception: {e}", exc_info=True)
            await self._mark_job_failed_in_db(job_id, str(e), finished_at, away_duration)
            await event_bus.emit(
                EventType.JOB_FAILED,
                job_id=job_id,
                data={
                    "job_id": job_id,
                    "status": JobStatus.FAILED.value,
                    "error": str(e),
                    "finished_at": finished_at.isoformat(),
                },
            )
            if final_state is not None:
                final_state["errors"].append(str(e))
                final_state["status"] = "FAILED"
                return final_state
            return {
                "job_id": job_id,
                "repo_path": repo_path,
                "task_prompt": task_prompt,
                "mode": mode,
                "status": "FAILED",
                "errors": [str(e)],
            }

    async def _handle_step_callback(self, state: AgentState, step_name: str) -> None:
        """Called whenever a node or step completes in the agent workflow."""
        job_id = state.get("job_id", "")
        current_step_idx = state.get("current_step_idx", 0)
        logger.debug(f"[{job_id}] Step update: {step_name} (step_idx={current_step_idx})")

        # Record step in SQLite DB
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            step = JobStep(
                job_id=job_id,
                step_index=current_step_idx,
                step_name=step_name,
                status=StepStatus.SUCCESS.value,
                stdout=f"Executed node: {step_name}",
            )
            session.add(step)
            try:
                await session.commit()
            except Exception as e:
                logger.warning(f"Could not persist step {step_name} to DB: {e}")
                await session.rollback()

        # Emit step completion event
        await event_bus.emit(
            EventType.STEP_COMPLETED,
            job_id=job_id,
            data={
                "step_index": current_step_idx,
                "step_name": step_name,
                "status": StepStatus.SUCCESS.value,
            },
        )

    async def _update_job_status_db(
        self,
        job_id: str,
        status: str,
        started_at: Optional[datetime] = None,
    ) -> None:
        """Updates job status and starting timestamp in SQLite."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = select(Job).filter(Job.id == job_id)
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if job:
                job.status = status
                if started_at:
                    job.started_at = started_at
                await session.commit()

    async def _persist_final_results(
        self,
        job_id: str,
        state: AgentState,
        finished_at: datetime,
        away_duration: float,
    ) -> None:
        """Persists health score, markdown report, findings, and diffs to SQLite."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = select(Job).filter(Job.id == job_id)
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if not job:
                return

            job.status = JobStatus.COMPLETED.value
            job.finished_at = finished_at
            job.away_duration_seconds = away_duration
            job.health_score = state.get("health_score")
            job.final_report_markdown = state.get("final_report_markdown")
            if state.get("errors"):
                job.error_message = "\n".join(state["errors"])

            # Save Findings
            for f in state.get("findings", []):
                # Ensure severity and category are valid strings
                sev = getattr(f.get("severity"), "value", f.get("severity", FindingSeverity.MEDIUM.value))
                cat = getattr(f.get("category"), "value", f.get("category", FindingCategory.DEAD_CODE.value))
                finding = Finding(
                    job_id=job_id,
                    severity=str(sev),
                    category=str(cat),
                    file_path=f.get("file_path", ""),
                    line_number=f.get("line_number"),
                    description=f.get("description", ""),
                    evidence=f.get("evidence"),
                    confidence=f.get("confidence", "HIGH"),
                    is_fixed=f.get("is_fixed", False),
                )
                session.add(finding)

            # Save Diffs
            for d in state.get("diffs", []):
                status_val = getattr(d.get("status"), "value", d.get("status", DiffStatus.VALIDATED.value))
                diff_obj = CodeDiff(
                    job_id=job_id,
                    file_path=d.get("file_path", ""),
                    diff_unified=d.get("diff_unified", ""),
                    status=str(status_val),
                )
                session.add(diff_obj)

            # Generate and Save Audio Briefing
            voice_script = state.get("voice_script")
            if voice_script:
                try:
                    audio_res = await elevenlabs_generator.generate_voice_briefing(job_id, voice_script)
                    if audio_res:
                        briefing = AudioBriefing(
                            job_id=job_id,
                            audio_path=audio_res["audio_path"],
                            script_text=audio_res["script_text"],
                            duration_seconds=audio_res.get("duration_seconds"),
                            provider=audio_res.get("provider", "elevenlabs"),
                            created_at=datetime.utcnow(),
                        )
                        session.add(briefing)
                        await event_bus.emit(
                            EventType.AUDIO_READY,
                            job_id=job_id,
                            data={"job_id": job_id, "audio_path": audio_res["audio_path"], "duration_seconds": audio_res.get("duration_seconds")},
                        )
                except Exception as audio_err:
                    logger.warning(f"[{job_id}] Audio briefing generation failed: {audio_err}")

            await session.commit()

    async def _mark_job_cancelled_in_db(
        self,
        job_id: str,
        finished_at: Optional[datetime] = None,
        away_duration: Optional[float] = None,
    ) -> None:
        """Marks a job as CANCELLED in SQLite."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = select(Job).filter(Job.id == job_id)
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if job:
                job.status = JobStatus.CANCELLED.value
                if finished_at:
                    job.finished_at = finished_at
                if away_duration is not None:
                    job.away_duration_seconds = away_duration
                await session.commit()

    async def _mark_job_failed_in_db(
        self,
        job_id: str,
        error_msg: str,
        finished_at: datetime,
        away_duration: float,
    ) -> None:
        """Marks a job as FAILED in SQLite with error message."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = select(Job).filter(Job.id == job_id)
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if job:
                job.status = JobStatus.FAILED.value
                job.error_message = error_msg
                job.finished_at = finished_at
                job.away_duration_seconds = away_duration
                await session.commit()


# Global singleton job runner orchestrator
job_runner = JobRunner()
