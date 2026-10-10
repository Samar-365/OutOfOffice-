"""Configuration management for OutOfOffice AI.

Handles environment variable loading, model presets (Gemma 2, CodeGemma),
Ollama endpoint resolution, database connection strings, Sentry telemetry,
ElevenLabs voice briefing parameters, and agent execution safety constraints.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global Application Settings."""

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Application Information
    APP_NAME: str = "OutOfOffice AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Local-First Autonomous AI Coding Agent (Hacktoberfest 2026: Touch Grass)"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API Server Configuration
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database Configuration (SQLite Local Persistence)
    DATA_DIR: Path = Path(__file__).resolve().parent.parent.parent / "data"
    DB_FILENAME: str = "outofoffice.db"
    
    @property
    def SQLITE_DATABASE_URL(self) -> str:
        """Returns synchronous SQLite connection string."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        db_path = self.DATA_DIR / self.DB_FILENAME
        return f"sqlite:///{db_path}"

    @property
    def ASYNC_SQLITE_DATABASE_URL(self) -> str:
        """Returns asynchronous aiosqlite connection string."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        db_path = self.DATA_DIR / self.DB_FILENAME
        return f"sqlite+aiosqlite:///{db_path}"

    # Local AI Inference Engine (Ollama + Gemma 2 / CodeGemma)
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434", description="Ollama local server endpoint")
    DEFAULT_MODEL: str = Field(default="gemma2:2b", description="Primary open-weight model for agent reasoning")
    FALLBACK_MODEL: str = Field(default="gemma2:2b", description="Lightweight model fallback for low VRAM systems")
    CODE_SPECIALIST_MODEL: str = Field(default="codegemma", description="Model used for AST synthesis and code patches")
    MODEL_TEMPERATURE: float = 0.2
    MODEL_TIMEOUT_SECONDS: int = 120

    # Observability & Partner Integrations: Sentry Agent Tracing
    SENTRY_DSN: Optional[str] = Field(default=None, description="Sentry DSN for distributed agent tracing")
    SENTRY_TRACES_SAMPLE_RATE: float = 1.0
    SENTRY_PROFILES_SAMPLE_RATE: float = 1.0

    # Voice Briefing & Partner Integrations: ElevenLabs
    ELEVENLABS_API_KEY: Optional[str] = Field(default=None, description="ElevenLabs API Key for voice summary")
    ELEVENLABS_VOICE_ID: str = Field(default="21m00Tcm4TlvDq8ikWAM", description="Rachel / default warm narrator voice")
    ELEVENLABS_MODEL_ID: str = "eleven_turbo_v2_5"
    AUDIO_ARTIFACTS_DIR: Path = Path(__file__).resolve().parent.parent.parent / "artifacts" / "audio"

    # Execution Sandbox & Safety Constraints
    MAX_COMMAND_TIMEOUT_SECONDS: int = 60
    MAX_FILE_SIZE_BYTES: int = 2 * 1024 * 1024  # 2 MB limit per inspected file
    AGENT_BRANCH_PREFIX: str = "agent/outofoffice-"
    ALLOW_REMOTE_GIT_PUSH: bool = False  # Strict safety: never push upstream automatically

    def ensure_directories(self) -> None:
        """Creates necessary local storage folders for artifacts and database."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.AUDIO_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = Settings()
settings.ensure_directories()
