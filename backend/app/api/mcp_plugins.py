"""MCP Plugin Management API routes."""
import uuid
from fastapi import APIRouter
from app.schemas.mcp_plugin import MCPServerCreate, MCPServerUpdate
from app.mcp.server_manager import MCPServerConfig
from app.mcp.security import SSRFProtector
from app.services.mcp_service import mcp_service

router = APIRouter(prefix="/mcp/plugins", tags=["mcp"])


@router.get("")
async def list_plugins():
    servers = await mcp_service.list_servers()
    return {"items": servers, "total": len(servers)}


@router.post("")
async def create_plugin(data: MCPServerCreate):
    url = SSRFProtector.validate_server_url(data.url)
    config = MCPServerConfig(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description or "",
        transport=data.transport,
        url=url,
        enabled=data.enabled,
        config=data.config or {},
    )
    await mcp_service.register_server(config)
    return {"id": config.id, "message": "Plugin registered"}


@router.put("/{plugin_id}")
async def update_plugin(plugin_id: str, data: MCPServerUpdate):
    # Fetch the existing server config to merge updates
    existing = await mcp_service.get_server(plugin_id)
    if not existing:
        return {"id": plugin_id, "updated": False, "error": "Plugin not found"}

    # Merge: only override fields that were explicitly provided
    update_dict = data.model_dump(exclude_unset=True)
    url = update_dict.pop("url", existing.get("url", ""))
    if url:
        url = SSRFProtector.validate_server_url(url)

    merged = MCPServerConfig(
        id=plugin_id,
        name=update_dict.get("name", existing.get("name", "")),
        description=update_dict.get("description", existing.get("description", "")),
        transport=update_dict.get("transport", existing.get("transport", "http")),
        url=url,
        enabled=update_dict.get("enabled", existing.get("enabled", True)),
        config=update_dict.get("config", existing.get("config", {})),
    )
    await mcp_service.register_server(merged)  # register_server does upsert
    return {"id": plugin_id, "updated": True}


@router.delete("/{plugin_id}")
async def delete_plugin(plugin_id: str):
    await mcp_service.remove_server(plugin_id)
    return {"deleted": True}


@router.post("/{plugin_id}/toggle")
async def toggle_plugin(plugin_id: str, data: dict):
    enabled = data.get("enabled", True)
    await mcp_service.toggle_server(plugin_id, enabled)
    return {"id": plugin_id, "enabled": enabled}


@router.post("/{plugin_id}/test")
async def test_plugin(plugin_id: str):
    return await mcp_service.test_server(plugin_id)


@router.get("/{plugin_id}/tools")
async def list_plugin_tools(plugin_id: str):
    tools = await mcp_service.discover_tools(plugin_id)
    return {"tools": [{"name": t.name, "description": t.description} for t in tools]}


@router.post("/{plugin_id}/tools/call")
async def call_plugin_tool(plugin_id: str, data: dict):
    return await mcp_service.call_tool(plugin_id, data["tool_name"], data.get("arguments", {}))
