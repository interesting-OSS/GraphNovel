"""MCP Service — DB-persisted service layer for Model Context Protocol integration.

MCP server configs are persisted to the mcp_plugins table, so they survive
service restarts. On startup, all enabled plugins are loaded from DB and
registered with the runtime manager.
"""
import json
import logging
from typing import Optional
from sqlalchemy import select
from app.database import async_session_factory
from app.models.mcp_plugin import MCPPlugin
from app.mcp.server_manager import MCPServerManager, MCPServerConfig, MCPTool

logger = logging.getLogger(__name__)


class MCPService:
    """Service-layer wrapper around MCPServerManager with DB persistence."""

    def __init__(self, manager: Optional[MCPServerManager] = None):
        self._manager = manager or MCPServerManager()
        self._tool_cache: dict[str, list[MCPTool]] = {}
        self._loaded = False

    @property
    def manager(self) -> MCPServerManager:
        return self._manager

    # ── Startup ─────────────────────────────────────────────────────────

    async def load_from_db(self):
        """Load all saved MCP plugin configs from DB on startup."""
        if self._loaded:
            return
        async with async_session_factory() as session:
            result = await session.execute(select(MCPPlugin))
            for row in result.scalars().all():
                cfg = json.loads(row.config) if row.config else {}
                config = MCPServerConfig(
                    id=row.id,
                    name=row.name,
                    description=row.description or "",
                    transport=row.transport,
                    url=row.url,
                    enabled=row.enabled,
                    config=cfg,
                )
                await self._manager.register_server(config)
            self._loaded = True
        servers = await self._manager.get_servers()
        logger.info("Loaded %d MCP plugins from DB", len(servers))

    # ── Server management ──────────────────────────────────────────────

    async def register_server(self, config: MCPServerConfig) -> bool:
        """Register a new MCP server and persist to DB (upsert if ID exists)."""
        try:
            async with async_session_factory() as session:
                result = await session.execute(
                    select(MCPPlugin).where(MCPPlugin.id == config.id))
                existing = result.scalar_one_or_none()
                if existing:
                    existing.name = config.name
                    existing.description = config.description
                    existing.transport = config.transport
                    existing.url = config.url
                    existing.enabled = config.enabled
                    existing.config = json.dumps(config.config, ensure_ascii=False)
                else:
                    session.add(MCPPlugin(
                        id=config.id, name=config.name,
                        description=config.description,
                        transport=config.transport, url=config.url,
                        enabled=config.enabled,
                        config=json.dumps(config.config, ensure_ascii=False),
                    ))
                await session.commit()

            await self._manager.register_server(config)
            self._tool_cache.pop(config.id, None)
            return True
        except Exception as e:
            logger.error("Failed to register MCP server %s: %s", config.id, e)
            return False

    async def remove_server(self, server_id: str) -> bool:
        """Remove a registered MCP server from runtime and DB."""
        try:
            # Remove from DB
            async with async_session_factory() as session:
                result = await session.execute(
                    select(MCPPlugin).where(MCPPlugin.id == server_id))
                row = result.scalar_one_or_none()
                if row:
                    await session.delete(row)
                    await session.commit()

            # Remove from runtime
            await self._manager.unregister_server(server_id)
            self._tool_cache.pop(server_id, None)
            return True
        except Exception as e:
            logger.error("Failed to remove MCP server %s: %s", server_id, e)
            return False

    async def toggle_server(self, server_id: str, enabled: bool) -> bool:
        """Enable or disable an MCP server. Updates DB + runtime."""
        try:
            # Update DB
            async with async_session_factory() as session:
                result = await session.execute(
                    select(MCPPlugin).where(MCPPlugin.id == server_id))
                row = result.scalar_one_or_none()
                if row:
                    row.enabled = enabled
                    await session.commit()

            # Update runtime
            config = await self._get_server_config(server_id)
            if config:
                config.enabled = enabled
                self._tool_cache.pop(server_id, None)
                if enabled:
                    await self._manager._discover_tools(server_id)
                return True
            return False
        except Exception as e:
            logger.error("Failed to toggle MCP server %s: %s", server_id, e)
            return False

    async def test_server(self, server_id: str) -> dict:
        """Test connectivity to an MCP server."""
        try:
            result = await self._manager.health_check(server_id)
            return {"server_id": server_id, "healthy": result, "error": None}
        except Exception as e:
            return {"server_id": server_id, "healthy": False, "error": str(e)}

    async def list_servers(self) -> list[dict]:
        """List all registered MCP servers."""
        servers = await self._manager.get_servers()
        return [
            {"id": s.id, "name": s.name, "description": s.description,
             "transport": s.transport, "url": s.url, "enabled": s.enabled}
            for s in servers
        ]

    async def get_server(self, server_id: str) -> Optional[dict]:
        """Get a single server config by ID."""
        config = await self._get_server_config(server_id)
        if not config:
            return None
        return {
            "id": config.id, "name": config.name, "description": config.description,
            "transport": config.transport, "url": config.url, "enabled": config.enabled,
            "config": config.config,
        }

    async def _get_server_config(self, server_id: str) -> Optional[MCPServerConfig]:
        servers = await self._manager.get_servers()
        for s in servers:
            if s.id == server_id:
                return s
        return None

    # ── Tool management ─────────────────────────────────────────────────

    async def discover_tools(self, server_id: str) -> list[MCPTool]:
        """Discover tools from an MCP server, with caching."""
        if server_id in self._tool_cache:
            return self._tool_cache[server_id]
        tools = await self._manager.list_server_tools(server_id)
        self._tool_cache[server_id] = tools
        return tools

    async def list_all_tools(self) -> list[dict]:
        """List tools from all enabled servers."""
        all_tools = []
        servers = await self._manager.get_servers()
        for config in servers:
            if not config.enabled:
                continue
            try:
                tools = await self.discover_tools(config.id)
                for tool in tools:
                    all_tools.append({
                        "name": tool.name, "description": tool.description,
                        "parameters": tool.parameters,
                        "server_id": config.id, "server_name": config.name,
                    })
            except Exception as e:
                logger.warning("Failed to discover tools from %s: %s", config.id, e)
        return all_tools

    async def call_tool(self, server_id: str, tool_name: str, arguments: dict) -> dict:
        return await self._manager.call_tool(server_id, tool_name, arguments)

    def clear_cache(self, server_id: Optional[str] = None):
        if server_id:
            self._tool_cache.pop(server_id, None)
        else:
            self._tool_cache.clear()


# Singleton
mcp_service = MCPService()
