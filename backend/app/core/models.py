"""SQLAlchemy ORM models for OutOfOffice AI.

Persists Jobs, Steps, AST Findings, Unified Code Diffs, and ElevenLabs Audio Briefings.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class JobMode(str, Enum):
    """Operation mode of the autonomous agent."""
    AUDIT = "AUDIT"  # Read-only analysis and test execution
    FIX = "FIX"      # Isolated branch fixes with test validation


class JobStatus(str, Enum):
    """Lifecycle status of an agent job."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class StepStatus(str, Enum):
    """Execution status of an individual plan step."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class FindingSeverity(str, Enum):
    """Severity classification of detected issues."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class FindingCategory(str, Enum):
    """Category classification of findings."""
    DEAD_CODE = "DEAD_CODE"
    TEST_FAILURE = "TEST_FAILURE"
    LINT_ERROR = "LINT_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    UNUSED_DEPENDENCY = "UNUSED_DEPENDENCY"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    SECURITY_WARNING = "SECURITY_WARNING"


class DiffStatus(str, Enum):
    """Status of code patches created by the agent."""
    PROPOSED = "PROPOSED"
    APPLIED = "APPLIED"
    VALIDATED = "VALIDATED"
    ROLLED_BACK = "ROLLED_BACK"


def generate_uuid() -> str:
    """Generates a UUID4 string as primary key."""
    return str(uuid.uuid4())


class Job(Base):
    """Master record for an autonomous coding job."""
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    repo_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    task_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default=JobMode.AUDIT.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.QUEUED.value, nullable=False, index=True)
    
    # Git details
    base_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    agent_branch: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Results & Health Metrics
    health_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # 0 to 100
    final_report_markdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Timing & "Touch Grass" Duration Tracking
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    away_duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Relationships
    steps: Mapped[List["JobStep"]] = relationship(
        "JobStep",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobStep.step_index",
    )
    findings: Mapped[List["Finding"]] = relationship(
        "Finding",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="Finding.created_at",
    )
    diffs: Mapped[List["CodeDiff"]] = relationship(
        "CodeDiff",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="CodeDiff.created_at",
    )
    audio_briefing: Mapped[Optional["AudioBriefing"]] = relationship(
        "AudioBriefing",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Job object to dictionary safely with async SQLAlchemy."""
        d = {
            "id": self.id,
            "repo_path": self.repo_path,
            "task_prompt": self.task_prompt,
            "mode": self.mode,
            "status": self.status,
            "base_branch": self.base_branch,
            "agent_branch": self.agent_branch,
            "health_score": self.health_score,
            "final_report_markdown": self.final_report_markdown,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "away_duration_seconds": self.away_duration_seconds,
            "step_count": len(self.steps) if "steps" in self.__dict__ and self.steps else 0,
            "finding_count": len(self.findings) if "findings" in self.__dict__ and self.findings else 0,
            "diff_count": len(self.diffs) if "diffs" in self.__dict__ and self.diffs else 0,
            "has_audio": "audio_briefing" in self.__dict__ and self.audio_briefing is not None,
        }
        return d


class JobStep(Base):
    """Step execution entry in the agent plan timeline."""
    __tablename__ = "job_steps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=StepStatus.PENDING.value, nullable=False)
    
    # Output & Diagnostics
    stdout: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    stderr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="steps")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes JobStep object to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "step_index": self.step_index,
            "step_name": self.step_name,
            "tool_name": self.tool_name,
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "latency_ms": self.latency_ms,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Finding(Base):
    """Individual code issue, dead code item, or test failure discovered."""
    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), default=FindingSeverity.MEDIUM.value, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default=FindingCategory.DEAD_CODE.value, nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[str] = mapped_column(String(20), default="HIGH", nullable=False)  # HIGH, MEDIUM, LOW
    is_fixed: Mapped[bool] = mapped_column(default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="findings")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes Finding object to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "severity": self.severity,
            "category": self.category,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "description": self.description,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "is_fixed": self.is_fixed,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class CodeDiff(Base):
    """Unified code diff generated during Fix Mode."""
    __tablename__ = "code_diffs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    original_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    patched_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    diff_unified: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=DiffStatus.VALIDATED.value, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="diffs")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes CodeDiff object to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "file_path": self.file_path,
            "diff_unified": self.diff_unified,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AudioBriefing(Base):
    """ElevenLabs voice debriefing audio metadata and script."""
    __tablename__ = "audio_briefings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("jobs.id", ondelete="CASCADE"), unique=True, nullable=False)
    audio_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    script_text: Mapped[str] = mapped_column(Text, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="elevenlabs", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    job: Mapped["Job"] = relationship("Job", back_populates="audio_briefing")

    def to_dict(self) -> Dict[str, Any]:
        """Serializes AudioBriefing object to dictionary."""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "audio_path": self.audio_path,
            "script_text": self.script_text,
            "duration_seconds": self.duration_seconds,
            "provider": self.provider,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
