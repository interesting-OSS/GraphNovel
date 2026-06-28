"""MCP Service — DB-persisted service layer wrapping MCPClientFacade.

On startup, loads all enabled plugins from DB and registers them with
the facade. Provides CRUD operations that sync DB + runtime state.
"""
import json
import logging
from typing import Optional
from sqlalchemy import select
from app.database import async_session_factory
from app.models.mcp_plugin import MCPPlugin
from app.mcp.facade import MCPClientFacade, mcp_client, MCPError

logger = logging.getLogger(__name__)


class MCPService:
    """Service-layer wrapper around MCPClientFacade with DB persistence."""

    def __init__(self, facade: Optional[MCPClientFacade] = None):
        self._facade = facade or mcp_client
        self._loaded = False

    @property
    def facade(self) -> MCPClientFacade:
        return self._facade

    # ── Startup ─────────────────────────────────────────────────────────

    async def load_from_db(self):
        """Load all enabled MCP plugin configs from DB on startup."""
        if self._loaded:
            return
        async with async_session_factory() as session:
            result = await session.execute(
                select(MCPPlugin).where(MCPPlugin.enabled == True)
            )
            rows = result.scalars().all()
            for row in rows:
                cfg = json.loads(row.config) if row.config else {}
                try:
                    await self._facade.register(
                        server_id=row.id,
                        plugin_name=row.plugin_name,
                        url=row.url,
                        transport=row.transport,
                        headers=cfg.get("headers"),
                    )
                except Exception as e:
                    logger.warning("Failed to register MCP plugin %s on startup: %s", row.plugin_name, e)
            self._loaded = True
        stats = self._facade.get_session_stats()
        logger.info("Loaded %d MCP plugins from DB", stats["total"])

    # ── Server management ──────────────────────────────────────────────

    async def register_server(self, server_id: str, plugin_name: str,
                              url: str, transport: str = "streamable_http",
                              description: str = "", config: dict = None,
                              enabled: bool = True) -> bool:
        """Register a new MCP server and persist to DB."""
        try:
            # Persist to DB
            async with async_session_factory() as session:
                result = await session.execute(
                    select(MCPPlugin).where(MCPPlugin.id == server_id))
                existing = result.scalar_one_or_none()
                if existing:
                    existing.plugin_name = plugin_name
                    existing.description = description
                    existing.transport = transport
                    existing.url = url
                    existing.enabled = enabled
                    existing.config = json.dumps(config or {}, ensure_ascii=False)
                else:
                    session.add(MCPPlugin(
                        id=server_id, plugin_name=plugin_name,
                        description=description, transport=transport,
                        url=url, enabled=enabled,
                        config=json.dumps(config or {}, ensure_ascii=False),
                    ))
                await session.commit()

            # Register with facade
            await self._facade.register(
                server_id=server_id, plugin_name=plugin_name,
                url=url, transport=transport,
                headers=(config or {}).get("headers"),
            )
            return True
        except Exception as e:
            logger.error("Failed to register MCP server %s: %s", server_id, e)
            return False

    async def remove_server(self, server_id: str) -> bool:
        """Remove a registered MCP server from runtime and DB."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(MCPPlugin).where(MCPPlugin.id == server_id))
                row = result.scalar_one_or_none()
                if row:
                    await session.delete(row)
                    await session.commit()
            await self._facade.unregister(server_id)
            return True
        except Exception as e:
            logger.error("Failed to remove MCP server %s: %s", server_id, e)
            return False

    async def toggle_server(self, server_id: str, enabled: bool) -> bool:
        """Enable or disable an MCP server."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(MCPPlugin).where(MCPPlugin.id == server_id))
                row = result.scalar_one_or_none()
                if row:
                    row.enabled = enabled
                    await session.commit()
            if not enabled:
                await self._facade.unregister(server_id)
            return True
        except Exception as e:
            logger.error("Failed to toggle MCP server %s: %s", server_id, e)
            return False

    async def test_server(self, server_id: str) -> dict:
        """Test connectivity to an MCP server."""
        return await self._facade.test_connection(server_id)

    async def list_servers(self) -> list[dict]:
        """List all registered MCP servers with their current status."""
        sessions = self._facade.get_session_stats()
        result = []
        for sid, info in sessions.get("sessions", {}).items():
            result.append({
                "id": sid,
                "name": info["plugin_name"],
                "status": info["status"],
                "error_count": info["error_count"],
                "uptime_seconds": info["uptime_seconds"],
            })
        return result

    async def get_server(self, server_id: str) -> Optional[dict]:
        """Get a single server by ID."""
        sessions = self._facade.get_session_stats()
        info = sessions.get("sessions", {}).get(server_id)
        if not info:
            return None
        return {"id": server_id, "name": info["plugin_name"], "status": info["status"]}

    # ── Tool management ─────────────────────────────────────────────────

    async def discover_tools(self, server_id: str) -> list[dict]:
        """Get tools for a server (from cache, auto-refresh if expired)."""
        return await self._facade.get_tools(server_id)

    async def list_all_tools(self) -> list[dict]:
        """List tools from all enabled servers in OpenAI Function Calling format."""
        return self._facade.format_tools_for_openai()

    async def call_tool(self, server_id: str, tool_name: str, arguments: dict) -> dict:
        """Call a tool on an MCP server with auto-reconnect."""
        return await self._facade.call_tool(server_id, tool_name, arguments)

    # ── Metrics & Cache ─────────────────────────────────────────────────

    def get_metrics(self, server_id: Optional[str] = None) -> dict:
        return self._facade.get_metrics(server_id)

    def get_cache_stats(self) -> dict:
        return self._facade.get_cache_stats()

    def clear_cache(self, server_id: Optional[str] = None):
        if server_id:
            self._facade._tool_cache.pop(server_id, None)
        else:
            self._facade._tool_cache.clear()


# Singleton
mcp_service = MCPService()
