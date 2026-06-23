"""Background task service — Celery-backed async task manager.

Each long-running operation (batch generate, batch analyze, batch polish,
book import) runs as a Celery task. Progress is persisted to PostgreSQL
and can be queried by the API for SSE relay to the frontend.

Lifecycle:  pending → running → completed / failed
                         ↘ paused → running / cancelled
"""

import json
import logging
from datetime import datetime
from typing import Optional
from sqlalchemy import select
from app.database import async_session_factory
from app.models.background_task import BackgroundTask
from app.celery_app import app as celery_app

logger = logging.getLogger(__name__)

# Map task type → Celery task name
_TASK_ROUTES = {
    "batch_generate": "batch_generate",
    "batch_analyze": "batch_analyze",
    "batch_polish": "batch_polish",
    "book_import": "book_import",
}


class TaskService:
    """Manages background task lifecycle via Celery + PostgreSQL."""

    async def create(
        self,
        project_id: str,
        task_type: str,
        config: dict,
    ) -> str:
        """Create a background task record in DB and enqueue to Celery.

        Returns the task ID for status polling.
        """
        async with async_session_factory() as session:
            task = BackgroundTask(
                project_id=project_id,
                task_type=task_type,
                status="pending",
                progress=0.0,
                config=json.dumps(config, ensure_ascii=False),
                can_pause=task_type in ("batch_generate", "batch_analyze", "batch_polish"),
                can_cancel=True,
            )
            session.add(task)
            await session.commit()
            task_id = task.id

        # Enqueue to Celery
        celery_task_name = _TASK_ROUTES.get(task_type)
        if celery_task_name:
            try:
                celery_app.send_task(
                    celery_task_name,
                    args=[task_id, project_id, config],
                    task_id=task_id,
                )
            except Exception as e:
                logger.error("Failed to enqueue Celery task %s: %s", task_id, e)
                await self._fail(task_id, f"Celery enqueue failed: {e}")
                raise

        return task_id

    async def get(self, task_id: str) -> Optional[dict]:
        """Get a single task by ID."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            return self._to_dict(task) if task else None

    async def list(self, project_id: Optional[str] = None) -> list[dict]:
        """List tasks, optionally filtered by project."""
        async with async_session_factory() as session:
            stmt = select(BackgroundTask).order_by(BackgroundTask.created_at.desc()).limit(100)
            if project_id:
                stmt = stmt.where(BackgroundTask.project_id == project_id)
            result = await session.execute(stmt)
            return [self._to_dict(t) for t in result.scalars().all()]

    async def cancel(self, task_id: str) -> bool:
        """Cancel a task if its status allows it."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return False
            if not task.can_cancel or task.status not in ("pending", "running", "paused"):
                return False

            task.status = "cancelled"
            task.updated_at = datetime.now()
            await session.commit()

            # Revoke the Celery task if still queued
            try:
                celery_app.control.revoke(task_id, terminate=True)
            except Exception:
                pass

            return True

    async def pause(self, task_id: str) -> bool:
        """Pause a running task."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return False
            if not task.can_pause or task.status != "running":
                return False

            task.status = "paused"
            task.updated_at = datetime.now()
            await session.commit()
            return True

    async def resume(self, task_id: str) -> bool:
        """Resume a paused task."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return False
            if task.status != "paused":
                return False

            task.status = "running"
            task.updated_at = datetime.now()
            await session.commit()
            return True

    async def delete(self, task_id: str) -> bool:
        """Delete a terminal (completed/failed/cancelled) task."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return False
            if task.status not in ("completed", "failed", "cancelled"):
                return False

            await session.delete(task)
            await session.commit()
            return True

    async def cleanup_stale(self):
        """Mark any running/pending tasks as failed on startup."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(
                    BackgroundTask.status.in_(("pending", "running"))
                )
            )
            for task in result.scalars().all():
                task.status = "failed"
                task.error_message = "Service restarted — task was interrupted"
                task.updated_at = datetime.now()
            await session.commit()

    async def _fail(self, task_id: str, error: str):
        """Internal: mark a task as failed."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.error_message = error
                task.updated_at = datetime.now()
                await session.commit()

    @staticmethod
    def _to_dict(task: BackgroundTask) -> dict:
        return {
            "id": task.id,
            "project_id": task.project_id,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "config": json.loads(task.config) if task.config else {},
            "result": json.loads(task.result) if task.result else None,
            "error_message": task.error_message,
            "can_pause": task.can_pause,
            "can_cancel": task.can_cancel,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


# Singleton
task_service = TaskService()
