"""Reset stale tasks on server startup.

Marks any tasks that were PENDING or RUNNING as FAILED when the server
was previously shut down uncleanly.
"""
from datetime import datetime, timezone, timedelta
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.background_task import BackgroundTask
from app.logging_config import get_logger

logger = get_logger(__name__)


async def reset_stale_tasks(db: AsyncSession, max_age_minutes: int = 30):
    """Mark stale pending/running tasks as failed on startup.

    Args:
        db: Database session
        max_age_minutes: Tasks older than this will be reset
    """
    cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)
    stmt = (
        update(BackgroundTask)
        .where(
            BackgroundTask.status.in_(["pending", "running"]),
            BackgroundTask.created_at < cutoff,
        )
        .values(
            status="failed",
            error_message="Service restarted — task was interrupted",
            updated_at=datetime.utcnow(),
        )
    )
    result = await db.execute(stmt)
    await db.commit()
    if result.rowcount > 0:
        logger.warning("Reset %d stale tasks on startup", result.rowcount)
