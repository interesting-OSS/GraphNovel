"""MCP module — production-grade plugin management.

Architecture:
  - facade.py: MCPClientFacade singleton (connection/session/tool/cache/metrics)
  - config.py: MCPConfig immutable constants
  - status_sync.py: async DB persistence of PluginStatus changes
  - security.py: SSRF protection (kept from original)

Usage:
    from app.mcp import mcp_client
    await mcp_client.initialize()
    await mcp_client.register("id", "name", "https://...", "streamable_http")
    tools = await mcp_client.get_tools("id")
    result = await mcp_client.call_tool("id", "search", {"q": "..."})
"""
from app.mcp.config import MCPConfig, mcp_config
from app.mcp.facade import (
    MCPClientFacade, MCPError, PluginStatus,
    SessionInfo, ToolCacheEntry, ToolMetrics,
    mcp_client,
)
from app.mcp.status_sync import (
    register_status_sync, shutdown_status_sync,
    enqueue_status_change,
)
from app.mcp.security import SSRFProtector

__all__ = [
    "MCPClientFacade", "MCPConfig", "mcp_config", "MCPError", "PluginStatus",
    "SessionInfo", "ToolCacheEntry", "ToolMetrics", "SSRFProtector",
    "mcp_client",
    "register_status_sync", "shutdown_status_sync", "enqueue_status_change",
]
