"""Database retry decorator using tenacity.

Handles transient database errors (OperationalError, DeadlockError)
with exponential backoff. Use on critical write operations.
"""
import logging
from sqlalchemy.exc import OperationalError, InternalError
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log,
)

logger = logging.getLogger(__name__)

# Detect deadlock across PostgreSQL and SQLite
try:
    from sqlalchemy.exc import DeadlockError  # type: ignore[attr-defined]
except ImportError:
    DeadlockError = InternalError  # SQLite fallback

db_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
    retry=retry_if_exception_type((OperationalError, InternalError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
"""Decorator for database operations that may encounter transient errors.

Usage:
    from app.utils.db_retry import db_retry

    @db_retry
    async def create_project_with_chapters(project_data, chapters, db):
        ...
"""
