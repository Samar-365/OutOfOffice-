"""SQLite Persistence & Re-hydration Engine for OutOfOffice AI.

Ensures zero state loss by immediately committing execution steps, AST findings,
code diffs, and audio briefings to SQLite. Provides comprehensive rehydration
capabilities when a developer reopens or refreshes the web application.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload

from app.agent.state import AgentState, create_initial_agent_state
from app.core.database import get_async_session_factory
from app.core.models import (
    AudioBriefing,
    CodeDiff,
    DiffStatus,
    Finding,
    FindingCategory,
    FindingSeverity,
    Job,
    JobMode,
    JobStatus,
    JobStep,
    StepStatus,
)

logger = logging.getLogger("outofoffice.services.persistence")


class PersistenceService:
    """Provides atomic persistence and durable state rehydration across browser sessions."""

    def __init__(self):
        self._session_factory = get_async_session_factory()

    async def save_step(
        self,
        job_id: str,
        step_index: int,
        step_name: str,
        tool_name: Optional[str] = None,
        status: str = StepStatus.SUCCESS.value,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        latency_ms: Optional[float] = None,
    ) -> JobStep:
        """Immediately commits an execution step entry to SQLite."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            step = JobStep(
                job_id=job_id,
                step_index=step_index,
                step_name=step_name,
                tool_name=tool_name,
                status=status,
                stdout=stdout,
                stderr=stderr,
                latency_ms=latency_ms,
                created_at=datetime.utcnow(),
            )
            session.add(step)
            await session.commit()
            await session.refresh(step)
            logger.debug(f"[{job_id}] Persisted step #{step_index}: {step_name} ({status}).")
            return step

    async def save_finding(
        self,
        job_id: str,
        file_path: str,
        description: str,
        severity: str = FindingSeverity.MEDIUM.value,
        category: str = FindingCategory.DEAD_CODE.value,
        line_number: Optional[int] = None,
        evidence: Optional[str] = None,
        confidence: str = "HIGH",
        is_fixed: bool = False,
    ) -> Finding:
        """Immediately commits a single detected finding to SQLite."""
        sev_str = getattr(severity, "value", severity)
        cat_str = getattr(category, "value", category)

        session_factory = get_async_session_factory()
        async with session_factory() as session:
            finding = Finding(
                job_id=job_id,
                severity=str(sev_str),
                category=str(cat_str),
                file_path=file_path,
                line_number=line_number,
                description=description,
                evidence=evidence,
                confidence=confidence,
                is_fixed=is_fixed,
                created_at=datetime.utcnow(),
            )
            session.add(finding)
            await session.commit()
            await session.refresh(finding)
            logger.debug(f"[{job_id}] Persisted finding: {file_path}:{line_number or 0} [{cat_str}].")
            return finding

    async def save_findings_batch(
        self,
        job_id: str,
        findings: List[Dict[str, Any]],
    ) -> List[Finding]:
        """Persists a list of findings to SQLite in a single transaction."""
        if not findings:
            return []

        session_factory = get_async_session_factory()
        persisted_findings: List[Finding] = []
        async with session_factory() as session:
            for f in findings:
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
                    created_at=datetime.utcnow(),
                )
                session.add(finding)
                persisted_findings.append(finding)
            await session.commit()
            logger.debug(f"[{job_id}] Persisted batch of {len(findings)} findings.")
        return persisted_findings

    async def save_diff(
        self,
        job_id: str,
        file_path: str,
        diff_unified: str,
        original_content: Optional[str] = None,
        patched_content: Optional[str] = None,
        status: str = DiffStatus.VALIDATED.value,
    ) -> CodeDiff:
        """Immediately commits a unified code diff to SQLite."""
        status_str = getattr(status, "value", status)
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            diff_obj = CodeDiff(
                job_id=job_id,
                file_path=file_path,
                original_content=original_content,
                patched_content=patched_content,
                diff_unified=diff_unified,
                status=str(status_str),
                created_at=datetime.utcnow(),
            )
            session.add(diff_obj)
            await session.commit()
            await session.refresh(diff_obj)
            logger.debug(f"[{job_id}] Persisted diff for {file_path}.")
            return diff_obj

    async def save_audio_briefing(
        self,
        job_id: str,
        audio_path: str,
        script_text: str,
        duration_seconds: Optional[float] = None,
        provider: str = "elevenlabs",
    ) -> AudioBriefing:
        """Persists ElevenLabs voice briefing metadata to SQLite."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            # Check if briefing exists for job
            stmt = select(AudioBriefing).filter(AudioBriefing.job_id == job_id)
            res = await session.execute(stmt)
            briefing = res.scalar_one_or_none()

            if briefing:
                briefing.audio_path = audio_path
                briefing.script_text = script_text
                briefing.duration_seconds = duration_seconds
                briefing.provider = provider
            else:
                briefing = AudioBriefing(
                    job_id=job_id,
                    audio_path=audio_path,
                    script_text=script_text,
                    duration_seconds=duration_seconds,
                    provider=provider,
                    created_at=datetime.utcnow(),
                )
                session.add(briefing)

            await session.commit()
            await session.refresh(briefing)
            logger.debug(f"[{job_id}] Persisted audio briefing: {audio_path}.")
            return briefing

    async def update_job_status(
        self,
        job_id: str,
        status: Optional[str] = None,
        started_at: Optional[datetime] = None,
        finished_at: Optional[datetime] = None,
        away_duration_seconds: Optional[float] = None,
        health_score: Optional[int] = None,
        final_report_markdown: Optional[str] = None,
        error_message: Optional[str] = None,
        base_branch: Optional[str] = None,
        agent_branch: Optional[str] = None,
    ) -> Optional[Job]:
        """Updates top-level Job metadata, execution metrics, and health scores."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = select(Job).filter(Job.id == job_id)
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if not job:
                logger.warning(f"Cannot update job {job_id}: record not found in SQLite.")
                return None

            if status is not None:
                job.status = getattr(status, "value", status)
            if started_at is not None:
                job.started_at = started_at
            if finished_at is not None:
                job.finished_at = finished_at
            if away_duration_seconds is not None:
                job.away_duration_seconds = away_duration_seconds
            if health_score is not None:
                job.health_score = health_score
            if final_report_markdown is not None:
                job.final_report_markdown = final_report_markdown
            if error_message is not None:
                job.error_message = error_message
            if base_branch is not None:
                job.base_branch = base_branch
            if agent_branch is not None:
                job.agent_branch = agent_branch

            await session.commit()
            await session.refresh(job)
            return job

    async def rehydrate_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Re-hydrates complete historical timeline and state for a returning developer.

        Loads all steps, AST findings, diffs, audio briefing, and health metrics.
        """
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = (
                select(Job)
                .options(
                    selectinload(Job.steps),
                    selectinload(Job.findings),
                    selectinload(Job.diffs),
                    selectinload(Job.audio_briefing),
                )
                .filter(Job.id == job_id)
            )
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if not job:
                return None

            # Build full structured dictionary representation
            data = job.to_dict()
            data["steps"] = [s.to_dict() for s in job.steps]
            data["findings"] = [f.to_dict() for f in job.findings]
            data["diffs"] = [d.to_dict() for d in job.diffs]
            data["audio_briefing"] = job.audio_briefing.to_dict() if job.audio_briefing else None

            # Compute timeline & progress indicators
            total_steps = len(job.steps)
            data["total_steps"] = total_steps
            data["last_step"] = job.steps[-1].step_name if job.steps else None
            data["is_complete"] = job.status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELLED.value]

            logger.info(f"[{job_id}] Successfully re-hydrated job state ({total_steps} steps, {len(job.findings)} findings).")
            return data

    async def rehydrate_agent_state(self, job_id: str) -> Optional[AgentState]:
        """Reconstructs an AgentState TypedDict from SQLite records for agent continuation."""
        job_data = await self.rehydrate_job(job_id)
        if not job_data:
            return None

        state = create_initial_agent_state(
            job_id=job_id,
            repo_path=job_data["repo_path"],
            task_prompt=job_data["task_prompt"],
            mode=job_data.get("mode", "AUDIT"),
        )

        state["status"] = job_data.get("status", "QUEUED")
        state["health_score"] = job_data.get("health_score")
        state["final_report_markdown"] = job_data.get("final_report_markdown")
        state["base_branch"] = job_data.get("base_branch")
        state["agent_branch"] = job_data.get("agent_branch")
        state["away_duration_seconds"] = job_data.get("away_duration_seconds", 0.0)

        if job_data.get("error_message"):
            state["errors"] = [job_data["error_message"]]

        # Reconstruct findings
        state["findings"] = [
            {
                "severity": f["severity"],
                "category": f["category"],
                "file_path": f["file_path"],
                "line_number": f.get("line_number"),
                "description": f["description"],
                "evidence": f.get("evidence"),
                "confidence": f.get("confidence", "HIGH"),
                "is_fixed": f.get("is_fixed", False),
            }
            for f in job_data.get("findings", [])
        ]

        # Reconstruct diffs
        state["diffs"] = [
            {
                "file_path": d["file_path"],
                "diff_unified": d["diff_unified"],
                "status": d.get("status", "VALIDATED"),
            }
            for d in job_data.get("diffs", [])
        ]

        # Reconstruct step history
        state["current_step_idx"] = len(job_data.get("steps", []))
        return state

    async def get_job_timeline(self, job_id: str) -> List[Dict[str, Any]]:
        """Returns chronologically ordered execution steps for waterfall timeline visualizers."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = select(JobStep).filter(JobStep.job_id == job_id).order_by(JobStep.step_index)
            res = await session.execute(stmt)
            steps = res.scalars().all()
            return [s.to_dict() for s in steps]

    async def get_findings_summary(self, job_id: str) -> Dict[str, Any]:
        """Summarizes findings count grouped by severity and category."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = select(Finding).filter(Finding.job_id == job_id)
            res = await session.execute(stmt)
            findings = res.scalars().all()

            by_severity: Dict[str, int] = {}
            by_category: Dict[str, int] = {}
            fixed_count = 0

            for f in findings:
                by_severity[f.severity] = by_severity.get(f.severity, 0) + 1
                by_category[f.category] = by_category.get(f.category, 0) + 1
                if f.is_fixed:
                    fixed_count += 1

            return {
                "job_id": job_id,
                "total": len(findings),
                "fixed": fixed_count,
                "by_severity": by_severity,
                "by_category": by_category,
            }


# Global singleton persistence service
persistence_service = PersistenceService()
