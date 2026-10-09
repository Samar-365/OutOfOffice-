"""Sentry Agent Tracing & Telemetry Spans for OutOfOffice AI.

Instruments LangGraph autonomous agent execution, tool invocations, and local model
inferences with Sentry distributed tracing spans (`ai.agent`, `ai.tool.call`,
`ai.model.inference`). Also maintains an in-memory waterfall telemetry ledger
for local offline visualization on the frontend trace screen.
"""

from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
import logging
import time
import uuid
from typing import Any, Dict, Generator, List, Optional

from app.core.config import settings

logger = logging.getLogger("outofoffice.integrations.sentry")

# Try importing sentry_sdk safely
try:
    import sentry_sdk
    from sentry_sdk.tracing import Span
    _SENTRY_AVAILABLE = True
except ImportError:
    sentry_sdk = None
    Span = None
    _SENTRY_AVAILABLE = False


class SpanRecord:
    """Represents an individual telemetry span in the execution waterfall."""

    def __init__(
        self,
        span_id: str,
        job_id: str,
        op: str,
        description: str,
        parent_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        tags: Optional[Dict[str, str]] = None,
    ):
        self.span_id = span_id
        self.job_id = job_id
        self.op = op
        self.description = description
        self.parent_id = parent_id
        self.data = data or {}
        self.tags = tags or {}
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.duration_ms: Optional[float] = None
        self.status: str = "running"
        self._start_perf = time.perf_counter()

    def finish(self, status: str = "ok", error_message: Optional[str] = None) -> None:
        """Finishes the span and calculates precise elapsed latency."""
        self._end_perf = time.perf_counter()
        self.duration_ms = round((self._end_perf - self._start_perf) * 1000.0, 2)
        self.end_time = datetime.utcnow()
        self.status = status
        if error_message:
            self.data["error"] = error_message

    def to_dict(self) -> Dict[str, Any]:
        """Serializes span record to a JSON-compatible dictionary."""
        return {
            "span_id": self.span_id,
            "job_id": self.job_id,
            "op": self.op,
            "description": self.description,
            "parent_id": self.parent_id,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "data": self.data,
            "tags": self.tags,
        }


class SentryTelemetryManager:
    """Manages Sentry distributed agent tracing and local telemetry waterfalls."""

    def __init__(self):
        self._spans: Dict[str, List[SpanRecord]] = {}
        self._initialized = False

    def init_sentry(
        self,
        dsn: Optional[str] = None,
        environment: Optional[str] = None,
        release: Optional[str] = None,
    ) -> bool:
        """Initializes Sentry SDK if DSN is configured."""
        active_dsn = dsn or settings.SENTRY_DSN
        if not _SENTRY_AVAILABLE or not active_dsn:
            logger.info("Sentry DSN not provided or SDK unavailable. Running local tracing mode.")
            self._initialized = False
            return False

        try:
            sentry_sdk.init(
                dsn=active_dsn,
                traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
                profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
                environment=environment or settings.ENVIRONMENT,
                release=release or f"outofoffice@{settings.APP_VERSION}",
            )
            self._initialized = True
            logger.info("Sentry Agent Tracing SDK successfully initialized.")
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize Sentry SDK: {e}")
            self._initialized = False
            return False

    @property
    def is_enabled(self) -> bool:
        """Returns True if Sentry integration is active."""
        return _SENTRY_AVAILABLE and self._initialized and sentry_sdk is not None

    def _record_span(self, span: SpanRecord) -> None:
        """Stores span record into in-memory ledger for the given job_id."""
        if span.job_id not in self._spans:
            self._spans[span.job_id] = []
        self._spans[span.job_id].append(span)

    @asynccontextmanager
    async def trace_agent_job(
        self,
        job_id: str,
        repo_path: str,
        mode: str,
        model_name: Optional[str] = None,
    ):
        """Root span wrapping entire autonomous agent job execution (`ai.agent`)."""
        span_id = str(uuid.uuid4())
        record = SpanRecord(
            span_id=span_id,
            job_id=job_id,
            op="ai.agent",
            description=f"Agent Run: {mode} mode on {repo_path}",
            tags={"job_id": job_id, "mode": mode, "repo": repo_path, "model": model_name or settings.DEFAULT_MODEL},
        )
        self._record_span(record)

        sentry_span = None
        if self.is_enabled:
            sentry_span = sentry_sdk.start_transaction(
                name=f"OutOfOffice Agent ({mode})",
                op="ai.agent",
            )
            sentry_span.set_tag("job_id", job_id)
            sentry_span.set_tag("mode", mode)
            sentry_span.set_data("repo_path", repo_path)

        try:
            yield record
            record.finish(status="ok")
            if sentry_span:
                sentry_span.set_status("ok")
        except Exception as e:
            record.finish(status="error", error_message=str(e))
            if sentry_span:
                sentry_span.set_status("internal_error")
            self.capture_error(e, job_id=job_id, context={"span": "ai.agent"})
            raise
        finally:
            if sentry_span:
                sentry_span.finish()

    @asynccontextmanager
    async def trace_step(
        self,
        job_id: str,
        step_name: str,
        step_index: int,
        parent_id: Optional[str] = None,
    ):
        """Span wrapping an individual reasoning step (`ai.step.execution`)."""
        span_id = str(uuid.uuid4())
        record = SpanRecord(
            span_id=span_id,
            job_id=job_id,
            op="ai.step.execution",
            description=f"Step #{step_index}: {step_name}",
            parent_id=parent_id,
            tags={"job_id": job_id, "step_index": str(step_index), "step_name": step_name},
        )
        self._record_span(record)

        sentry_span = None
        if self.is_enabled:
            sentry_span = sentry_sdk.start_span(
                op="ai.step.execution",
                description=f"Step {step_index}: {step_name}",
            )

        try:
            yield record
            record.finish(status="ok")
            if sentry_span:
                sentry_span.set_status("ok")
        except Exception as e:
            record.finish(status="error", error_message=str(e))
            if sentry_span:
                sentry_span.set_status("internal_error")
            self.capture_error(e, job_id=job_id, context={"step": step_name})
            raise
        finally:
            if sentry_span:
                sentry_span.finish()

    @asynccontextmanager
    async def trace_tool(
        self,
        tool_name: str,
        job_id: str,
        args: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
    ):
        """Span wrapping deterministic tool invocations (`ai.tool.call`)."""
        span_id = str(uuid.uuid4())
        record = SpanRecord(
            span_id=span_id,
            job_id=job_id,
            op="ai.tool.call",
            description=f"Tool: {tool_name}",
            parent_id=parent_id,
            data={"args": args or {}},
            tags={"job_id": job_id, "tool_name": tool_name},
        )
        self._record_span(record)

        sentry_span = None
        if self.is_enabled:
            sentry_span = sentry_sdk.start_span(
                op="ai.tool.call",
                description=f"Tool Execution: {tool_name}",
            )
            sentry_span.set_data("tool_args", args or {})

        try:
            yield record
            record.finish(status="ok")
            if sentry_span:
                sentry_span.set_status("ok")
        except Exception as e:
            record.finish(status="error", error_message=str(e))
            if sentry_span:
                sentry_span.set_status("internal_error")
            raise
        finally:
            if sentry_span:
                sentry_span.finish()

    @asynccontextmanager
    async def trace_model_inference(
        self,
        job_id: str,
        model_name: str,
        prompt_preview: Optional[str] = None,
        temperature: Optional[float] = None,
        parent_id: Optional[str] = None,
    ):
        """Span wrapping local model generation inference (`ai.model.inference`)."""
        span_id = str(uuid.uuid4())
        record = SpanRecord(
            span_id=span_id,
            job_id=job_id,
            op="ai.model.inference",
            description=f"Inference: {model_name}",
            parent_id=parent_id,
            data={
                "model": model_name,
                "temperature": temperature or settings.MODEL_TEMPERATURE,
                "prompt_preview": (prompt_preview[:200] + "...") if prompt_preview and len(prompt_preview) > 200 else prompt_preview,
            },
            tags={"job_id": job_id, "model": model_name},
        )
        self._record_span(record)

        sentry_span = None
        if self.is_enabled:
            sentry_span = sentry_sdk.start_span(
                op="ai.model.inference",
                description=f"Local Model: {model_name}",
            )
            sentry_span.set_tag("model", model_name)

        try:
            yield record
            record.finish(status="ok")
            if sentry_span:
                sentry_span.set_status("ok")
        except Exception as e:
            record.finish(status="error", error_message=str(e))
            if sentry_span:
                sentry_span.set_status("internal_error")
            raise
        finally:
            if sentry_span:
                sentry_span.finish()

    def capture_error(
        self,
        error: Exception,
        job_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Captures an exception to Sentry with attached job context."""
        logger.error(f"[{job_id or 'global'}] Capturing error: {error}")
        if self.is_enabled:
            with sentry_sdk.push_scope() as scope:
                if job_id:
                    scope.set_tag("job_id", job_id)
                if context:
                    for k, v in context.items():
                        scope.set_extra(k, v)
                sentry_sdk.capture_exception(error)

    def get_job_spans(self, job_id: str) -> List[Dict[str, Any]]:
        """Returns all recorded telemetry spans for a job in chronological order."""
        records = self._spans.get(job_id, [])
        return [r.to_dict() for r in records]

    def export_waterfall(self, job_id: str) -> Dict[str, Any]:
        """Synthesizes an exportable Sentry trace waterfall structure."""
        records = self._spans.get(job_id, [])
        spans_dict = [r.to_dict() for r in records]

        total_latency_ms = sum(r.duration_ms or 0.0 for r in records if r.op == "ai.step.execution")
        tool_latency_ms = sum(r.duration_ms or 0.0 for r in records if r.op == "ai.tool.call")
        inference_latency_ms = sum(r.duration_ms or 0.0 for r in records if r.op == "ai.model.inference")

        tool_calls_count = sum(1 for r in records if r.op == "ai.tool.call")
        inferences_count = sum(1 for r in records if r.op == "ai.model.inference")
        errors_count = sum(1 for r in records if r.status == "error")

        return {
            "job_id": job_id,
            "total_spans": len(records),
            "total_execution_ms": round(total_latency_ms, 2),
            "tool_execution_ms": round(tool_latency_ms, 2),
            "model_inference_ms": round(inference_latency_ms, 2),
            "tool_calls_count": tool_calls_count,
            "inferences_count": inferences_count,
            "errors_count": errors_count,
            "spans": spans_dict,
        }

    def clear_spans(self, job_id: Optional[str] = None) -> None:
        """Cleans up in-memory spans ledger."""
        if job_id:
            self._spans.pop(job_id, None)
        else:
            self._spans.clear()


# Global singleton sentry telemetry instance
sentry_tracer = SentryTelemetryManager()
