"""MCP plugin status synchronization — async DB writer.

Uses an asyncio.Queue to decouple status change notifications from
the main request path. A background worker drains the queue and
persists PluginStatus changes to the mcp_plugins table.
"""
import asyncio
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Queue of (server_id, status_value, error_message) tuples
_status_queue: asyncio.Queue = asyncio.Queue()
_sync_task: asyncio.Task | None = None


async def _sync_worker():
    """Background worker: drain the queue and persist status to DB."""
    from app.database import async_session_factory
    from app.models.mcp_plugin import MCPPlugin
    from sqlalchemy import select

    while True:
        try:
            server_id, status, error_msg = await _status_queue.get()
            try:
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(MCPPlugin).where(MCPPlugin.id == server_id)
                    )
                    plugin = result.scalar_one_or_none()
                    if plugin:
                        plugin.mcp_status = status
                        plugin.mcp_error = error_msg
                        plugin.last_checked = datetime.now(timezone.utc)
                        await session.commit()
                        logger.debug("Synced MCP status for %s: %s", server_id, status)
            except Exception as e:
                logger.error("Failed to sync MCP status for %s: %s", server_id, e)
            finally:
                _status_queue.task_done()
        except asyncio.CancelledError:
            break
        except Exception:
            await asyncio.sleep(1)


def register_status_sync():
    """Start the status sync background worker. Call once at startup."""
    global _sync_task
    if _sync_task is None or _sync_task.done():
        _sync_task = asyncio.create_task(_sync_worker())
        logger.info("MCP status sync worker started")


async def enqueue_status_change(server_id: str, status: str, error_message: str = ""):
    """Enqueue a status change for async persistence."""
    await _status_queue.put((server_id, status, error_message))


async def shutdown_status_sync():
    """Cancel the sync worker and drain remaining items."""
    global _sync_task
    if _sync_task and not _sync_task.done():
        # Drain remaining items
        remaining = _status_queue.qsize()
        if remaining > 0:
            logger.info("Draining %d pending MCP status sync items", remaining)
            try:
                await asyncio.wait_for(_status_queue.join(), timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("Timed out draining MCP status queue")
        _sync_task.cancel()
        try:
            await _sync_task
        except asyncio.CancelledError:
            pass
    logger.info("MCP status sync worker stopped")
