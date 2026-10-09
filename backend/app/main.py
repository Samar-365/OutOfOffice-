"""Main FastAPI application entrypoint for OutOfOffice AI.

Local-first autonomous AI coding agent designed for Hacktoberfest 2026 ("Touch Grass").
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.api.schemas import HealthResponse
from app.core.config import settings
from app.core.database import init_db
from app.core.events import EventType, event_bus
from app.services.job_runner import job_runner

# Configure Logging
logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("outofoffice.main")


# Application Lifespan (Startup & Shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle events for FastAPI application."""
    logger.info("Initializing OutOfOffice AI storage directories & database...")
    settings.ensure_directories()
    init_db()

    # Optional Sentry initialization
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=settings.SENTRY_DSN,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
                environment=settings.ENVIRONMENT,
                release=f"outofoffice@{settings.APP_VERSION}",
            )
            logger.info("Sentry Agent Tracing successfully initialized.")
        except Exception as e:
            logger.warning(f"Could not initialize Sentry: {e}")

    logger.info(f"OutOfOffice AI v{settings.APP_VERSION} ready. Local model: {settings.DEFAULT_MODEL}")
    yield
    logger.info("Shutting down OutOfOffice AI backend...")
    await job_runner.stop_all_jobs()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION,
    lifespan=lifespan,
)

# CORS Middleware for local frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Audio Artifacts Folder
if settings.AUDIO_ARTIFACTS_DIR.exists():
    app.mount("/artifacts/audio", StaticFiles(directory=str(settings.AUDIO_ARTIFACTS_DIR)), name="audio_artifacts")

# Include REST API Routers
app.include_router(api_router)


# Health Check
@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """System health check endpoint."""
    return HealthResponse(
        status="ok",
        app_name=settings.APP_NAME,
        app_version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        default_model=settings.DEFAULT_MODEL,
        timestamp=datetime.utcnow().isoformat(),
    )


# WebSocket Endpoints
@app.websocket("/ws/jobs/{job_id}")
async def websocket_job_stream(websocket: WebSocket, job_id: str):
    """Real-time telemetry event stream for a specific job."""
    await event_bus.connect_job(websocket, job_id)
    try:
        # Send initial connection confirmation event
        await websocket.send_json({
            "type": EventType.HEARTBEAT.value,
            "job_id": job_id,
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": f"Connected to telemetry stream for job {job_id}"},
        })
        while True:
            # Keep connection alive; listen for pings or client messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await event_bus.disconnect_job(websocket, job_id)
    except Exception as e:
        logger.warning(f"WebSocket error on job {job_id}: {e}")
        await event_bus.disconnect_job(websocket, job_id)


@app.websocket("/ws/dashboard")
async def websocket_dashboard_stream(websocket: WebSocket):
    """Real-time global event stream for the main dashboard."""
    await event_bus.connect_global(websocket)
    try:
        await websocket.send_json({
            "type": EventType.HEARTBEAT.value,
            "job_id": "global",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"message": "Connected to global dashboard stream"},
        })
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await event_bus.disconnect_global(websocket)
    except Exception as e:
        logger.warning(f"Global WebSocket error: {e}")
        await event_bus.disconnect_global(websocket)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)
