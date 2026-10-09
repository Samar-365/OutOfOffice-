"""Unit tests for ElevenLabs Voice Debrief Generator (Submodule 7.2)."""

import asyncio
from pathlib import Path
import pytest
import httpx

from app.core.config import settings
from app.integrations.elevenlabs_brief import ElevenLabsVoiceGenerator, elevenlabs_generator


def test_is_configured_property(monkeypatch):
    gen = ElevenLabsVoiceGenerator()

    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", None)
    assert gen.is_configured is False

    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "   ")
    assert gen.is_configured is False

    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", "sk_test_123456789")
    assert gen.is_configured is True


def test_estimate_duration_seconds():
    gen = ElevenLabsVoiceGenerator()
    assert gen.estimate_duration_seconds("") == 0.0

    # 140 words is roughly 60 seconds
    text_140_words = " ".join(["word"] * 140)
    assert round(gen.estimate_duration_seconds(text_140_words)) == 60

    # 70 words is roughly 30 seconds
    text_70_words = " ".join(["word"] * 70)
    assert round(gen.estimate_duration_seconds(text_70_words)) == 30


def test_generate_mock_briefing(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_ARTIFACTS_DIR", tmp_path)
    gen = ElevenLabsVoiceGenerator()

    job_id = "test-mock-audio-job"
    script = "Welcome back! You touched grass for 25 minutes while tests were resolved."
    result = gen.generate_mock_briefing(job_id=job_id, script_text=script)

    assert result["job_id"] == job_id
    assert result["provider"] == "elevenlabs-simulated"
    assert result["script_text"] == script
    assert result["duration_seconds"] > 0

    audio_file = Path(result["audio_path"])
    assert audio_file.exists()
    assert audio_file.stat().st_size > 0


@pytest.mark.anyio
async def test_generate_voice_briefing_fallback_without_key(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(settings, "ELEVENLABS_API_KEY", None)

    gen = ElevenLabsVoiceGenerator()
    job_id = "test-no-key-job"
    script = "Welcome back! All builds green."

    result = await gen.generate_voice_briefing(job_id=job_id, script_text=script)
    assert result is not None
    assert result["job_id"] == job_id
    assert Path(result["audio_path"]).exists()


@pytest.mark.anyio
async def test_generate_voice_briefing_mock_http_success(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_ARTIFACTS_DIR", tmp_path)
    gen = ElevenLabsVoiceGenerator()
    job_id = "test-elevenlabs-http"
    script = "Welcome back! 3 files fixed."

    fake_mp3_content = b"\xff\xfb\x90\x44\x00\x00\x00\x00" * 20

    async def mock_post(self, url, *args, **kwargs):
        return httpx.Response(status_code=200, content=fake_mp3_content)

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    result = await gen.generate_voice_briefing(
        job_id=job_id,
        script_text=script,
        api_key="valid_mock_api_key",
    )

    assert result is not None
    assert result["job_id"] == job_id
    assert result["provider"] == "elevenlabs"

    audio_file = Path(result["audio_path"])
    assert audio_file.exists()
    assert audio_file.read_bytes() == fake_mp3_content


@pytest.mark.anyio
async def test_generate_voice_briefing_http_error_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_ARTIFACTS_DIR", tmp_path)
    gen = ElevenLabsVoiceGenerator()
    job_id = "test-elevenlabs-err"
    script = "Welcome back! Safe fallback test."

    async def mock_post_err(self, url, *args, **kwargs):
        return httpx.Response(status_code=401, content=b'{"detail":"Unauthorized"}')

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post_err)

    result = await gen.generate_voice_briefing(
        job_id=job_id,
        script_text=script,
        api_key="invalid_api_key",
    )

    assert result is not None
    assert result["provider"] == "elevenlabs-simulated"
    assert Path(result["audio_path"]).exists()
