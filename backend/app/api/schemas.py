"""Pydantic schemas for API request validation and structured responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RepoValidateRequest(BaseModel):
    """Request payload for validating a local repository."""
    repo_path: str = Field(..., description="Absolute path to the local repository directory")


class RepoValidateResponse(BaseModel):
    """Response payload with repository metadata."""
    is_valid: bool
    repo_path: str
    is_git_repo: bool
    current_branch: Optional[str] = None
    has_uncommitted_changes: bool = False
    detected_languages: List[str] = Field(default_factory=list)
    project_type: Optional[str] = None  # e.g. "React (TypeScript)", "Python (FastAPI)", "Rust"
    manifest_files: List[str] = Field(default_factory=list)
    test_framework: Optional[str] = None
    file_count: int = 0
    message: str = ""


class JobCreateRequest(BaseModel):
    """Request payload to create and launch a new autonomous job."""
    repo_path: str = Field(..., description="Absolute path to local Git repository")
    task_prompt: str = Field(..., description="Natural language task instructions")
    mode: str = Field(default="AUDIT", description="AUDIT (read-only) or FIX (branch-isolated changes)")
    model_override: Optional[str] = Field(default=None, description="Optional custom model (e.g. gemma2:9b)")


class JobResponse(BaseModel):
    """Standardized response representing a job's current status and results."""
    id: str
    repo_path: str
    task_prompt: str
    mode: str
    status: str
    base_branch: Optional[str] = None
    agent_branch: Optional[str] = None
    health_score: Optional[int] = None
    final_report_markdown: Optional[str] = None
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    away_duration_seconds: Optional[float] = None
    step_count: int = 0
    finding_count: int = 0
    diff_count: int = 0
    has_audio: bool = False
    steps: Optional[List[Dict[str, Any]]] = None
    findings: Optional[List[Dict[str, Any]]] = None
    diffs: Optional[List[Dict[str, Any]]] = None
    audio_briefing: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """System health response."""
    status: str = "ok"
    app_name: str
    app_version: str
    environment: str
    default_model: str
    timestamp: str
