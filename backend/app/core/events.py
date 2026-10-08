"""Event bus and WebSocket connection management for OutOfOffice AI.

Provides real-time pub/sub broadcasting of agent execution steps, findings,
diffs, and job lifecycle events to connected web clients.
"""

import asyncio
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from fastapi import WebSocket

logger = logging.getLogger("outofoffice.events")


class EventType(str, Enum):
    """Standardized event types emitted during agent execution."""
    JOB_CREATED = "JOB_CREATED"
    JOB_STARTED = "JOB_STARTED"
    STEP_STARTED = "STEP_STARTED"
    STEP_COMPLETED = "STEP_COMPLETED"
    STEP_FAILED = "STEP_FAILED"
    FINDING_DETECTED = "FINDING_DETECTED"
    DIFF_PRODUCED = "DIFF_PRODUCED"
    AUDIO_READY = "AUDIO_READY"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    JOB_CANCELLED = "JOB_CANCELLED"
    HEARTBEAT = "HEARTBEAT"


class AgentEvent:
    """Standardized event container."""

    def __init__(
        self,
        event_type: EventType,
        job_id: str,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        self.event_type = event_type
        self.job_id = job_id
        self.data = data or {}
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes event to JSON-compatible dictionary."""
        return {
            "type": self.event_type.value,
            "job_id": self.job_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }

    def to_json(self) -> str:
        """Serializes event to JSON string."""
        return json.dumps(self.to_dict())


class ConnectionManager:
    """Manages active WebSocket connections subscribed to specific job IDs."""

    def __init__(self):
        # Maps job_id -> set of active WebSockets
        self._active_connections: Dict[str, Set[WebSocket]] = {}
        # Global subscribers (e.g. for dashboard live job list)
        self._global_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect_job(self, websocket: WebSocket, job_id: str) -> None:
        """Registers a WebSocket connection for a specific job stream."""
        await websocket.accept()
        async with self._lock:
            if job_id not in self._active_connections:
                self._active_connections[job_id] = set()
            self._active_connections[job_id].add(websocket)
        logger.info(f"WebSocket client connected to job stream: {job_id}")

    async def connect_global(self, websocket: WebSocket) -> None:
        """Registers a WebSocket connection for global dashboard events."""
        await websocket.accept()
        async with self._lock:
            self._global_connections.add(websocket)
        logger.info("WebSocket client connected to global dashboard stream")

    async def disconnect_job(self, websocket: WebSocket, job_id: str) -> None:
        """Unregisters a WebSocket connection from a job stream."""
        async with self._lock:
            if job_id in self._active_connections:
                self._active_connections[job_id].discard(websocket)
                if not self._active_connections[job_id]:
                    del self._active_connections[job_id]
        logger.info(f"WebSocket client disconnected from job stream: {job_id}")

    async def disconnect_global(self, websocket: WebSocket) -> None:
        """Unregisters a WebSocket connection from the global stream."""
        async with self._lock:
            self._global_connections.discard(websocket)
        logger.info("WebSocket client disconnected from global stream")

    async def broadcast_to_job(self, job_id: str, event: AgentEvent) -> None:
        """Broadcasts an event to all clients subscribed to a given job_id."""
        json_payload = event.to_json()
        dead_connections: List[WebSocket] = []

        async with self._lock:
            connections = list(self._active_connections.get(job_id, set()))

        for ws in connections:
            try:
                await ws.send_text(json_payload)
            except Exception as e:
                logger.warning(f"Error sending message to WebSocket on job {job_id}: {e}")
                dead_connections.append(ws)

        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    if job_id in self._active_connections:
                        self._active_connections[job_id].discard(ws)

    async def broadcast_global(self, event: AgentEvent) -> None:
        """Broadcasts an event to all global dashboard clients."""
        json_payload = event.to_json()
        dead_connections: List[WebSocket] = []

        async with self._lock:
            connections = list(self._global_connections)

        for ws in connections:
            try:
                await ws.send_text(json_payload)
            except Exception as e:
                logger.warning(f"Error sending message to global WebSocket: {e}")
                dead_connections.append(ws)

        if dead_connections:
            async with self._lock:
                for ws in dead_connections:
                    self._global_connections.discard(ws)

    async def emit(self, event_type: EventType, job_id: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Convenience helper to construct and broadcast an AgentEvent."""
        event = AgentEvent(event_type=event_type, job_id=job_id, data=data)
        await self.broadcast_to_job(job_id, event)
        await self.broadcast_global(event)


# Global singleton event bus & connection manager
event_bus = ConnectionManager()
