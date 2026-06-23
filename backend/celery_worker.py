"""Celery worker entry point.

Start with:
    celery -A celery_worker worker --loglevel=info --pool=threads --concurrency=4

The --pool=threads is used because our tasks are I/O-bound (AI API calls)
and internally use asyncio.run() to execute async code.
"""
from app.celery_app import app  # noqa: F401
import app.celery_tasks as _  # noqa: F401 — explicit import ensures task registration
