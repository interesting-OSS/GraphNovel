"""Celery task definitions — delegates to TaskService for actual execution.

Each Celery task wrapper:
  1. Creates a TaskService instance
  2. Delegates to corresponding _run_batch_* method
  3. Handles error reporting

Note: Progress updates happen via BackgroundTask DB records updated by TaskService.
"""
import asyncio
import logging
from app.celery_app import app

logger = logging.getLogger(__name__)

# Import helper functions used by task_service
from app.services.task_service import _split_by_boundaries, _find_position  # noqa: F401


# ── Celery Task Helpers ──────────────────────────────────────────────────

def _run_async(coro):
    """Safely run async coroutine, works in both sync and async Celery pools."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    else:
        # Running inside an async event loop (e.g., gevent/asyncio pool)
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()


async def _execute_via_service(task_id: str, project_id: str, task_type: str, config: dict):
    """Delegate to TaskService for execution with proper DB progress tracking."""
    from app.services.task_service import TaskService
    svc = TaskService()
    await svc._execute(task_id, project_id, task_type, config)


# ── Celery Task Wrappers ──────────────────────────────────────────────────


@app.task(bind=True, name="batch_generate")
def run_batch_generate(self, task_id: str, project_id: str, config: dict):
    """Celery task: batch chapter generation."""
    try:
        _run_async(_execute_via_service(task_id, project_id, "batch_generate", config))
    except Exception as e:
        logger.exception("Batch generate task %s failed", task_id)
        raise


@app.task(bind=True, name="batch_analyze")
def run_batch_analyze(self, task_id: str, project_id: str, config: dict):
    """Celery task: batch chapter analysis."""
    try:
        _run_async(_execute_via_service(task_id, project_id, "batch_analyze", config))
    except Exception as e:
        logger.exception("Batch analyze task %s failed", task_id)
        raise


@app.task(bind=True, name="batch_polish")
def run_batch_polish(self, task_id: str, project_id: str, config: dict):
    """Celery task: batch chapter polish."""
    try:
        _run_async(_execute_via_service(task_id, project_id, "batch_polish", config))
    except Exception as e:
        logger.exception("Batch polish task %s failed", task_id)
        raise


@app.task(bind=True, name="book_import")
def run_book_import(self, task_id: str, project_id: str, config: dict):
    """Celery task: book file import and structuring."""
    try:
        _run_async(_execute_via_service(task_id, project_id, "book_import", config))
    except Exception as e:
        logger.exception("Book import task %s failed", task_id)
        raise
