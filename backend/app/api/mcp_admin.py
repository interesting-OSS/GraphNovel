"""MCP Admin endpoints — metrics, cache stats, session monitoring.

Split from mcp_plugins.py per 方案一 2.12 for cleaner API semantics.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Query
from app.mcp import mcp_client

router = APIRouter(prefix="/mcp", tags=["mcp_admin"])


@router.get("/metrics")
async def get_mcp_metrics(tool_name: Optional[str] = Query(None)):
    """Get per-tool call metrics (success rate, avg latency, call count)."""
    return {
        "metrics": mcp_client.get_metrics(tool_name),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/cache/stats")
async def get_cache_stats():
    """Get MCP tool cache statistics."""
    return {
        "cache_stats": mcp_client.get_cache_stats(),
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/cache/clear")
async def clear_cache(server_id: Optional[str] = None):
    """Clear the MCP tool cache, optionally for a specific server."""
    if server_id:
        mcp_client._tool_cache.pop(server_id, None)
    else:
        mcp_client._tool_cache.clear()
    return {"cleared": True, "server_id": server_id}


@router.get("/sessions/stats")
async def get_session_stats():
    """Get MCP session status overview."""
    return {
        "sessions": mcp_client.get_session_stats(),
        "timestamp": datetime.now().isoformat(),
    }
