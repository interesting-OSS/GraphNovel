"""Background task system — asyncio-based, replacing Celery."""
from app.tasks.task_queue import PerUserTaskQueue, Task, TaskStatus, TaskProgressTracker, queue_manager
from app.tasks.stale_task_reset import reset_stale_tasks

__all__ = [
    "PerUserTaskQueue", "Task", "TaskStatus", "TaskProgressTracker",
    "queue_manager", "reset_stale_tasks",
]
