"""Unit tests for Local Audio Streaming & Browser Web Speech Fallback (Submodule 7.3)."""

from pathlib import Path
import pytest

from app.core.config import settings
from app.integrations.audio_streamer import AudioStreamer, audio_streamer


@pytest.mark.anyio
async def test_stream_file_chunks(tmp_path):
    streamer = AudioStreamer()
    test_file = tmp_path / "test_audio.mp3"
    content = b"AUDIO_DATA_" * 1000
    test_file.write_bytes(content)

    chunks = []
    async for chunk in streamer.stream_file_chunks(test_file, chunk_size=512):
        chunks.append(chunk)

    assert len(chunks) > 1
    assert b"".join(chunks) == content


@pytest.mark.anyio
async def test_stream_file_chunks_nonexistent(tmp_path):
    streamer = AudioStreamer()
    non_existent = tmp_path / "missing.mp3"

    with pytest.raises(FileNotFoundError):
        async for _ in streamer.stream_file_chunks(non_existent):
            pass


def test_generate_local_tts_audio(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_ARTIFACTS_DIR", tmp_path)
    streamer = AudioStreamer()
    job_id = "test-job-local-tts"
    script = "Welcome back! While you touched grass, 2 bugs were resolved."

    res = streamer.generate_local_tts_audio(job_id=job_id, script_text=script)
    assert res["job_id"] == job_id
    assert res["script_text"] == script
    assert res["duration_seconds"] > 0
    assert Path(res["audio_path"]).exists()
    assert Path(res["audio_path"]).stat().st_size > 0


def test_get_web_speech_payload():
    streamer = AudioStreamer()
    job_id = "test-web-speech-job"
    script = "Welcome back! 42 files inspected."

    payload = streamer.get_web_speech_payload(
        job_id=job_id,
        script_text=script,
        voice_name="Google US English",
        rate=1.1,
    )

    assert payload["job_id"] == job_id
    assert payload["type"] == "web_speech_api"
    assert payload["text"] == script
    assert payload["voice_name"] == "Google US English"
    assert payload["rate"] == 1.1
    assert payload["estimated_duration_seconds"] > 0


def test_resolve_audio_strategy_file_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_ARTIFACTS_DIR", tmp_path)
    streamer = AudioStreamer()
    job_id = "test-strategy-file"

    audio_file = tmp_path / f"briefing-{job_id}.mp3"
    audio_file.write_bytes(b"MP3_DATA")

    strategy = streamer.resolve_audio_strategy(
        job_id=job_id,
        script_text="Finished job.",
        existing_audio_path=str(audio_file),
    )

    assert strategy["strategy"] == "file_stream"
    assert strategy["stream_url"] == f"/api/jobs/{job_id}/audio"
    assert strategy["audio_path"] == str(audio_file)
    assert strategy["file_size_bytes"] == len(b"MP3_DATA")


def test_resolve_audio_strategy_web_speech_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "AUDIO_ARTIFACTS_DIR", tmp_path)
    streamer = AudioStreamer()
    job_id = "test-strategy-fallback"

    strategy = streamer.resolve_audio_strategy(
        job_id=job_id,
        script_text="No audio file generated yet.",
        existing_audio_path=None,
    )

    assert strategy["strategy"] == "web_speech"
    assert "payload" in strategy
    assert strategy["payload"]["type"] == "web_speech_api"
    assert strategy["payload"]["text"] == "No audio file generated yet."
