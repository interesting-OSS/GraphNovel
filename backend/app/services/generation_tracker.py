"""In-memory generation status tracker — lightweight progress monitoring.

Tracks active AI generations so the frontend (or dev) can poll /api/info
and see what's currently running, which phase, and how long it's been going.
"""
import time
import threading
from typing import Optional
from datetime import datetime, timezone


class _GenStatus:
    """Snapshot of a single active generation."""
    __slots__ = ("phase", "label", "progress", "started_at", "last_update")
    def __init__(self, phase: str, label: str):
        self.phase = phase
        self.label = label
        self.progress: float = 0.0
        self.started_at = datetime.now(timezone.utc)
        self.last_update = self.started_at


class GenerationTracker:
    """Thread-safe tracker for active AI generations, keyed by project_id.

    Usage:
      tracker.start("proj-1", "world_build", "世界观构建")
      tracker.update("proj-1", progress=30.0, phase="generating")
      tracker.finish("proj-1")

    The /api/info endpoint reads this to show what's running.
    """

    _active: dict[str, _GenStatus] = {}
    _lock = threading.Lock()

    @classmethod
    def start(cls, project_id: str, phase: str, label: str) -> None:
        with cls._lock:
            cls._active[project_id] = _GenStatus(phase, label)

    @classmethod
    def update(cls, project_id: str, progress: Optional[float] = None,
               phase: Optional[str] = None, label: Optional[str] = None) -> None:
        with cls._lock:
            entry = cls._active.get(project_id)
            if entry is None:
                return
            if progress is not None:
                entry.progress = progress
            if phase is not None:
                entry.phase = phase
            if label is not None:
                entry.label = label
            entry.last_update = datetime.now(timezone.utc)

    @classmethod
    def finish(cls, project_id: str) -> None:
        with cls._lock:
            cls._active.pop(project_id, None)

    @classmethod
    def error(cls, project_id: str, message: str) -> None:
        with cls._lock:
            entry = cls._active.get(project_id)
            if entry:
                entry.phase = "error"
                entry.label = message
                entry.last_update = datetime.now(timezone.utc)

    @classmethod
    def snapshot(cls) -> dict:
        """Return {project_id: {...}} for all active generations."""
        with cls._lock:
            now = datetime.now(timezone.utc)
            return {
                pid: {
                    "phase": s.phase,
                    "label": s.label,
                    "progress": s.progress,
                    "started_at": s.started_at.isoformat(),
                    "elapsed_seconds": (now - s.started_at).total_seconds(),
                }
                for pid, s in cls._active.items()
            }


# Singleton
tracker = GenerationTracker()
