"""MCP Plugin Management API routes."""
import uuid
from fastapi import APIRouter
from app.schemas.mcp_plugin import MCPServerCreate, MCPServerUpdate
from app.mcp.security import SSRFProtector
from app.services.mcp_service import mcp_service
from app.logging_config import get_logger

router = APIRouter(prefix="/mcp/plugins", tags=["mcp"])
logger = get_logger(__name__)


# ── CRUD ────────────────────────────────────────────────────────────────────

@router.get("")
async def list_plugins():
    """List all registered MCP plugins with current status."""
    servers = await mcp_service.list_servers()
    return {"items": servers, "total": len(servers)}


@router.post("")
async def create_plugin(data: MCPServerCreate):
    """Register a new MCP plugin. SSRF validation is applied to the URL."""
    url = SSRFProtector.validate_server_url(str(data.url))
    server_id = str(uuid.uuid4())
    success = await mcp_service.register_server(
        server_id=server_id,
        plugin_name=data.name,
        url=url,
        transport=data.transport,
        description=data.description or "",
        config=data.config or {},
        enabled=data.enabled,
    )
    if not success:
        return {"id": server_id, "registered": False, "error": "Registration failed"}
    return {"id": server_id, "registered": True, "message": "Plugin registered"}


@router.put("/{plugin_id}")
async def update_plugin(plugin_id: str, data: MCPServerUpdate):
    """Update an existing MCP plugin configuration."""
    existing = await mcp_service.get_server(plugin_id)
    if not existing:
        return {"id": plugin_id, "updated": False, "error": "Plugin not found"}

    update_dict = data.model_dump(exclude_unset=True)
    url = str(update_dict.pop("url", "")) if "url" in update_dict else ""
    if url:
        url = SSRFProtector.validate_server_url(url)

    merged = {
        **existing,
        **update_dict,
        "url": url or existing.get("url", ""),
    }
    success = await mcp_service.register_server(
        server_id=plugin_id,
        plugin_name=merged.get("name", ""),
        url=merged.get("url", ""),
        transport=merged.get("transport", "streamable_http"),
        description=merged.get("description", ""),
        config=merged.get("config", {}),
        enabled=merged.get("enabled", True),
    )
    return {"id": plugin_id, "updated": success}


@router.delete("/{plugin_id}")
async def delete_plugin(plugin_id: str):
    """Remove a registered MCP plugin."""
    await mcp_service.remove_server(plugin_id)
    return {"deleted": True}


@router.post("/{plugin_id}/toggle")
async def toggle_plugin(plugin_id: str, data: dict):
    """Enable or disable an MCP plugin."""
    enabled = data.get("enabled", True)
    success = await mcp_service.toggle_server(plugin_id, enabled)
    return {"id": plugin_id, "enabled": enabled, "success": success}


@router.post("/{plugin_id}/test")
async def test_plugin(plugin_id: str):
    """Test connectivity to an MCP plugin."""
    return await mcp_service.test_server(plugin_id)


@router.get("/{plugin_id}/tools")
async def list_plugin_tools(plugin_id: str):
    """List tools exposed by an MCP plugin."""
    tools = await mcp_service.discover_tools(plugin_id)
    return {"tools": [{"name": t["name"], "description": t.get("description", "")} for t in tools]}


@router.post("/{plugin_id}/tools/call")
async def call_plugin_tool(plugin_id: str, data: dict):
    """Call a tool on an MCP plugin."""
    result = await mcp_service.call_tool(
        plugin_id, data["tool_name"], data.get("arguments", {})
    )
    return {"result": result}


# ── Admin endpoints (metrics, cache, sessions) ─────────────────────────────

@router.get("/admin/metrics")
async def get_mcp_metrics(server_id: str = None):
    """Get per-tool call metrics (success rate, avg latency, etc.)."""
    return mcp_service.get_metrics(server_id)


@router.get("/admin/cache")
async def get_cache_stats():
    """Get tool cache statistics."""
    return mcp_service.get_cache_stats()


@router.post("/admin/cache/clear")
async def clear_cache(server_id: str = None):
    """Clear the tool cache, optionally for a specific server."""
    mcp_service.clear_cache(server_id)
    return {"cleared": True, "server_id": server_id}
