"""Touch Grass Away-Time Tracker & Metrics Service for OutOfOffice AI.

Tracks real-time developer away-time from when the user clicks 'Go Touch Grass'
until return. Computes human-readable duration strings, gamified outdoor badges,
and all-time community screen-time saved statistics.
"""

from datetime import datetime
import logging
import math
from typing import Any, Dict, Optional
from sqlalchemy import func, select

from app.core.database import get_async_session_factory
from app.core.models import Job, JobStatus

logger = logging.getLogger("outofoffice.services.timer_service")


class GrassTimerService:
    """Calculates and formats developer away-time and screen-freedom metrics."""

    def __init__(self):
        self._active_timers: Dict[str, datetime] = {}

    def start_timer(self, job_id: str, start_time: Optional[datetime] = None) -> datetime:
        """Registers the start timestamp when developer steps away."""
        st = start_time or datetime.utcnow()
        self._active_timers[job_id] = st
        logger.info(f"[{job_id}] Grass timer started at {st.isoformat()}.")
        return st

    def stop_timer(self, job_id: str, end_time: Optional[datetime] = None) -> float:
        """Stops the active timer for a job and returns elapsed seconds."""
        et = end_time or datetime.utcnow()
        st = self._active_timers.pop(job_id, None)
        if not st:
            return 0.0
        duration = max(0.0, (et - st).total_seconds())
        logger.info(f"[{job_id}] Grass timer stopped. Duration: {duration:.2f}s.")
        return duration

    def get_elapsed_seconds(self, job_id: str) -> float:
        """Returns live elapsed seconds for an actively running job timer."""
        st = self._active_timers.get(job_id)
        if not st:
            return 0.0
        return max(0.0, (datetime.utcnow() - st).total_seconds())

    @staticmethod
    def format_duration_hhmmss(seconds: float) -> str:
        """Formats seconds into standard HH:MM:SS string (e.g. '00:24:18')."""
        total_seconds = max(0, int(seconds))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    @staticmethod
    def format_human_readable(seconds: float) -> str:
        """Formats seconds into warm, natural language for audio brief and UI display."""
        total_seconds = max(0, int(round(seconds)))
        if total_seconds < 60:
            return f"{total_seconds} second{'s' if total_seconds != 1 else ''} away from keyboard"

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
        if secs > 0 and hours == 0:
            parts.append(f"{secs} second{'s' if secs > 1 else ''}")

        return f"{' and '.join(parts)} away from keyboard"

    @staticmethod
    def get_grass_badge(seconds: float) -> Dict[str, str]:
        """Assigns a playful gamified badge based on outdoor away duration."""
        minutes = seconds / 60.0
        if minutes < 2.0:
            return {
                "tier": "Sprout Quick-Step",
                "icon": "🌱",
                "description": "Stepped outside for a quick deep breath of fresh air.",
            }
        elif minutes < 10.0:
            return {
                "tier": "Lawn Lounger",
                "icon": "🌿",
                "description": "Enjoyed a relaxing stroll in the yard while your code worked.",
            }
        elif minutes < 25.0:
            return {
                "tier": "Park Ranger",
                "icon": "🌳",
                "description": "True commitment to touching grass! Refreshed and energized.",
            }
        elif minutes < 60.0:
            return {
                "tier": "Forest Hermit",
                "icon": "🌲",
                "description": "Conquered the trail and unplugged from the digital grind.",
            }
        else:
            return {
                "tier": "Transcendental Grass God",
                "icon": "🏔️",
                "description": "Ultimate digital detox achieved. Fully recharged!",
            }

    def compute_grass_metrics(
        self,
        job_id: str,
        duration_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Calculates comprehensive grass metrics dictionary for results dashboard and audio briefing."""
        dur = duration_seconds if duration_seconds is not None else self.get_elapsed_seconds(job_id)
        dur = max(0.0, float(dur))

        badge = self.get_grass_badge(dur)
        human_text = self.format_human_readable(dur)
        hhmmss = self.format_duration_hhmmss(dur)
        minutes_away = round(dur / 60.0, 1)

        # Approximate 100 outdoor walking steps per minute
        estimated_steps = int(minutes_away * 100)

        return {
            "job_id": job_id,
            "duration_seconds": round(dur, 2),
            "minutes_away": minutes_away,
            "formatted_time": hhmmss,
            "human_readable": human_text,
            "badge": badge,
            "estimated_steps": estimated_steps,
            "screen_time_saved_minutes": minutes_away,
        }

    async def get_all_time_stats(self) -> Dict[str, Any]:
        """Aggregates all-time 'Touch Grass' statistics across completed jobs in SQLite."""
        session_factory = get_async_session_factory()
        async with session_factory() as session:
            stmt = select(
                func.count(Job.id).label("total_jobs"),
                func.sum(Job.away_duration_seconds).label("total_seconds"),
                func.max(Job.away_duration_seconds).label("max_seconds"),
                func.avg(Job.away_duration_seconds).label("avg_seconds"),
            ).filter(Job.status == JobStatus.COMPLETED.value)

            res = await session.execute(stmt)
            row = res.first()

            total_jobs = row.total_jobs or 0 if row else 0
            total_seconds = float(row.total_seconds or 0.0) if row else 0.0
            max_seconds = float(row.max_seconds or 0.0) if row else 0.0
            avg_seconds = float(row.avg_seconds or 0.0) if row else 0.0

            total_minutes = round(total_seconds / 60.0, 1)
            total_hours = round(total_seconds / 3600.0, 2)

            return {
                "total_completed_jobs": total_jobs,
                "total_grass_touched_seconds": round(total_seconds, 2),
                "total_grass_touched_minutes": total_minutes,
                "total_grass_touched_hours": total_hours,
                "formatted_total_time": self.format_duration_hhmmss(total_seconds),
                "longest_away_session_formatted": self.format_duration_hhmmss(max_seconds),
                "average_away_session_formatted": self.format_duration_hhmmss(avg_seconds),
                "all_time_badge": self.get_grass_badge(total_seconds),
            }


# Global singleton grass timer service
timer_service = GrassTimerService()
