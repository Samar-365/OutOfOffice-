"""Unit tests for Sentry Agent Tracing & Telemetry Spans (Submodule 7.1)."""

import asyncio
import pytest

from app.integrations.sentry_telemetry import (
    SentryTelemetryManager,
    SpanRecord,
    sentry_tracer,
)


def test_span_record_lifecycle():
    span = SpanRecord(
        span_id="span-123",
        job_id="job-abc",
        op="ai.tool.call",
        description="Tool: test_runner",
        tags={"tool": "pytest"},
    )
    assert span.status == "running"
    assert span.duration_ms is None

    # Simulate brief work
    span.finish(status="ok")
    assert span.status == "ok"
    assert span.duration_ms is not None
    assert span.duration_ms >= 0.0

    d = span.to_dict()
    assert d["span_id"] == "span-123"
    assert d["op"] == "ai.tool.call"
    assert d["status"] == "ok"


def test_sentry_init_fallback():
    manager = SentryTelemetryManager()
    # Initializing without DSN returns False and stays in local mode
    result = manager.init_sentry(dsn=None)
    assert result is False
    assert manager.is_enabled is False


@pytest.mark.anyio
async def test_tracing_context_managers_and_waterfall():
    manager = SentryTelemetryManager()
    job_id = "test-job-sentry-1"

    # 1. Root Agent Job Span
    async with manager.trace_agent_job(job_id=job_id, repo_path="/repo", mode="AUDIT", model_name="gemma2:9b"):
        # 2. Step Span
        async with manager.trace_step(job_id=job_id, step_name="Discovery", step_index=0):
            # 3. Tool Span
            async with manager.trace_tool(tool_name="repo_discovery", job_id=job_id, args={"path": "/repo"}):
                await asyncio.sleep(0.01)

        # 4. Model Inference Span
        async with manager.trace_model_inference(job_id=job_id, model_name="gemma2:9b", prompt_preview="Analyze repo"):
            await asyncio.sleep(0.01)

    spans = manager.get_job_spans(job_id)
    assert len(spans) == 4

    ops = [s["op"] for s in spans]
    assert "ai.agent" in ops
    assert "ai.step.execution" in ops
    assert "ai.tool.call" in ops
    assert "ai.model.inference" in ops

    # Test waterfall export
    waterfall = manager.export_waterfall(job_id)
    assert waterfall["job_id"] == job_id
    assert waterfall["total_spans"] == 4
    assert waterfall["tool_calls_count"] == 1
    assert waterfall["inferences_count"] == 1
    assert waterfall["errors_count"] == 0
    assert waterfall["total_execution_ms"] >= 0.0


@pytest.mark.anyio
async def test_tracing_error_capture():
    manager = SentryTelemetryManager()
    job_id = "test-job-sentry-err"

    with pytest.raises(ValueError, match="Simulated tool explosion"):
        async with manager.trace_agent_job(job_id=job_id, repo_path="/repo", mode="FIX"):
            async with manager.trace_tool(tool_name="broken_tool", job_id=job_id):
                raise ValueError("Simulated tool explosion")

    spans = manager.get_job_spans(job_id)
    assert len(spans) == 2
    assert spans[0]["status"] == "error"
    assert spans[1]["status"] == "error"

    waterfall = manager.export_waterfall(job_id)
    assert waterfall["errors_count"] == 2


def test_clear_spans():
    manager = SentryTelemetryManager()
    manager._record_span(SpanRecord(span_id="s1", job_id="j1", op="test", description="desc"))
    manager._record_span(SpanRecord(span_id="s2", job_id="j2", op="test", description="desc"))

    assert len(manager.get_job_spans("j1")) == 1
    manager.clear_spans("j1")
    assert len(manager.get_job_spans("j1")) == 0
    assert len(manager.get_job_spans("j2")) == 1

    manager.clear_spans()
    assert len(manager.get_job_spans("j2")) == 0
