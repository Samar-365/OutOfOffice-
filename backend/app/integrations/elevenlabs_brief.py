"""ElevenLabs Voice Debrief Generator for OutOfOffice AI.

Converts final agent execution reports into natural, friendly welcome-back voice
narrations using the ElevenLabs Text-to-Speech API. Saves generated .mp3 audio
artifacts for instant streaming playback upon developer return.
"""

from datetime import datetime
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger("outofoffice.integrations.elevenlabs")

# Minimal valid MP3 header frame for offline simulation/testing
_MOCK_MP3_BYTES = (
    b"\xff\xfb\x90\x44\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
    b"ID3\x04\x00\x00\x00\x00\x00#TSSE\x00\x00\x00\x0f\x00\x00\x03OutOfOffice AI"
)


class ElevenLabsVoiceGenerator:
    """Generates speech briefings using ElevenLabs API with offline resilience."""

    def __init__(self):
        self.api_base_url = "https://api.elevenlabs.io/v1"

    @property
    def is_configured(self) -> bool:
        """Returns True if a valid ElevenLabs API key is configured."""
        return bool(settings.ELEVENLABS_API_KEY and len(settings.ELEVENLABS_API_KEY.strip()) > 5)

    def estimate_duration_seconds(self, script_text: str) -> float:
        """Estimates spoken duration in seconds (~140 words per minute)."""
        words = len(script_text.strip().split())
        if words == 0:
            return 0.0
        return max(1.0, round((words / 140.0) * 60.0, 1))

    async def generate_voice_briefing(
        self,
        job_id: str,
        script_text: str,
        voice_id: Optional[str] = None,
        model_id: Optional[str] = None,
        api_key: Optional[str] = None,
        output_filename: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Generates an MP3 audio briefing from voice script text via ElevenLabs."""
        clean_key = (api_key or settings.ELEVENLABS_API_KEY or "").strip()
        active_voice = voice_id or settings.ELEVENLABS_VOICE_ID
        active_model = model_id or settings.ELEVENLABS_MODEL_ID

        settings.ensure_directories()
        fname = output_filename or f"briefing-{job_id}.mp3"
        dest_path = settings.AUDIO_ARTIFACTS_DIR / fname

        if not clean_key:
            logger.info(f"[{job_id}] No ElevenLabs API key configured. Generating local mock briefing.")
            return self.generate_mock_briefing(job_id=job_id, script_text=script_text, dest_path=dest_path)

        url = f"{self.api_base_url}/text-to-speech/{active_voice}"
        headers = {
            "xi-api-key": clean_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": script_text,
            "model_id": active_model,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True,
            },
        }

        try:
            logger.info(f"[{job_id}] Requesting ElevenLabs TTS generation for voice '{active_voice}'...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code != 200:
                    logger.error(f"[{job_id}] ElevenLabs API error ({resp.status_code}): {resp.text}")
                    return self.generate_mock_briefing(job_id=job_id, script_text=script_text, dest_path=dest_path)

                dest_path.write_bytes(resp.content)

            duration = self.estimate_duration_seconds(script_text)
            logger.info(f"[{job_id}] ElevenLabs voice briefing generated successfully at {dest_path} (~{duration}s).")

            return {
                "job_id": job_id,
                "audio_path": str(dest_path),
                "script_text": script_text,
                "duration_seconds": duration,
                "provider": "elevenlabs",
                "created_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.warning(f"[{job_id}] Failed to contact ElevenLabs API: {e}. Falling back to mock audio.")
            return self.generate_mock_briefing(job_id=job_id, script_text=script_text, dest_path=dest_path)

    def generate_mock_briefing(
        self,
        job_id: str,
        script_text: str,
        dest_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generates a playable placeholder MP3 file for offline test verification."""
        settings.ensure_directories()
        out_path = dest_path or (settings.AUDIO_ARTIFACTS_DIR / f"briefing-{job_id}.mp3")
        out_path.write_bytes(_MOCK_MP3_BYTES)
        duration = self.estimate_duration_seconds(script_text)

        logger.info(f"[{job_id}] Created offline simulation audio briefing at {out_path}.")
        return {
            "job_id": job_id,
            "audio_path": str(out_path),
            "script_text": script_text,
            "duration_seconds": duration,
            "provider": "elevenlabs-simulated",
            "created_at": datetime.utcnow().isoformat(),
        }


# Global singleton ElevenLabs voice generator instance
elevenlabs_generator = ElevenLabsVoiceGenerator()
