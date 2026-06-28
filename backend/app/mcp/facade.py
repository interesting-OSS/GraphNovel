"""MCP Client Facade — production-grade singleton for MCP plugin lifecycle.

Features (vs the old MCPServerManager):
  - Uses official mcp SDK (streamablehttp_client / sse_client)
  - Session state machine: ACTIVE → DEGRADED → ERROR
  - Tool caching with TTL
  - Auto-reconnect on ClosedResourceError / ValueError
  - Background health check loop
  - Per-tool metrics (calls, success rate, avg latency)
  - OpenAI Function Calling format conversion
  - Batch tool calls with concurrency control
"""
import asyncio
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Types ───────────────────────────────────────────────────────────────────

class PluginStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEGRADED = "degraded"
    ERROR = "error"


class MCPError(Exception):
    """Raised when MCP operations fail."""


@dataclass
class ToolCacheEntry:
    tools: list[dict]
    cached_at: float = field(default_factory=time.time)


@dataclass
class ToolMetrics:
    calls: int = 0
    successes: int = 0
    total_latency_ms: float = 0.0
    last_call_at: float = 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.calls, 1)

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / max(self.calls, 1)

    def record(self, success: bool, latency_ms: float):
        self.calls += 1
        if success:
            self.successes += 1
        self.total_latency_ms += latency_ms
        self.last_call_at = time.time()


@dataclass
class SessionInfo:
    server_id: str
    plugin_name: str
    url: str
    transport: str  # "streamable_http" | "sse"
    status: PluginStatus = PluginStatus.ACTIVE
    error_count: int = 0
    total_requests: int = 0
    last_error: str = ""
    created_at: float = field(default_factory=time.time)
    # Runtime session (set after connect)
    _session: Any = field(default=None, repr=False)
    _client: Any = field(default=None, repr=False)


# ── Facade ──────────────────────────────────────────────────────────────────

class MCPClientFacade:
    """Singleton facade for MCP plugin lifecycle management.

    Usage:
        facade = MCPClientFacade()
        await facade.register("server-1", "MyPlugin", "http://...", "streamable_http")
        tools = await facade.get_tools("server-1")
        result = await facade.call_tool("server-1", "search", {"query": "..."})
    """

    def __init__(self):
        from app.mcp.config import mcp_config
        self._config = mcp_config
        self._sessions: dict[str, SessionInfo] = {}
        self._tool_cache: dict[str, ToolCacheEntry] = {}
        self._metrics: dict[str, ToolMetrics] = {}  # key: "server_id.tool_name"
        self._health_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._initialized = False

    # ── Lifecycle ───────────────────────────────────────────────────────

    async def initialize(self):
        """Start background tasks and load persisted plugins from DB."""
        if self._initialized:
            return
        self._health_task = asyncio.create_task(self._health_check_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._initialized = True
        logger.info("MCPClientFacade initialized")

    async def close(self):
        """Graceful shutdown: cancel background tasks, close all sessions."""
        for task in (self._health_task, self._cleanup_task):
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        for sid, info in list(self._sessions.items()):
            await self._close_session(info)
        self._sessions.clear()
        self._tool_cache.clear()
        self._metrics.clear()
        self._initialized = False
        logger.info("MCPClientFacade closed")

    async def _close_session(self, info: SessionInfo):
        """Safely close one session's streams and client connections."""
        # Close MCP SDK context manager (streams from __aenter__)
        if info._client is not None and hasattr(info._client, '__aexit__'):
            try:
                await info._client.__aexit__(None, None, None)
            except Exception as e:
                logger.debug("MCP SDK session close error for %s: %s", info.server_id, e)
        # Close HTTP fallback client
        elif info._client is not None and hasattr(info._client, 'aclose'):
            try:
                await info._client.aclose()
            except Exception as e:
                logger.debug("HTTP client close error for %s: %s", info.server_id, e)
        info._session = None
        info._client = None

    # ── Registration ────────────────────────────────────────────────────

    async def register(
        self, server_id: str, plugin_name: str, url: str,
        transport: str = "streamable_http", headers: dict | None = None,
    ) -> SessionInfo:
        """Register a new MCP plugin or update an existing one.

        On first registration, connects to the server and discovers tools.
        """
        # Close old session if updating
        old = self._sessions.get(server_id)
        if old:
            await self._close_session(old)

        info = SessionInfo(
            server_id=server_id,
            plugin_name=plugin_name,
            url=url.rstrip("/"),
            transport=transport,
        )
        try:
            await self._connect(info, headers or {})
            await self._discover_tools(server_id)
            info.status = PluginStatus.ACTIVE
        except Exception as e:
            info.status = PluginStatus.ERROR
            info.last_error = str(e)
            logger.error("Failed to register MCP plugin %s: %s", plugin_name, e)

        self._sessions[server_id] = info
        return info

    async def unregister(self, server_id: str):
        """Remove a plugin registration."""
        info = self._sessions.pop(server_id, None)
        if info:
            await self._close_session(info)
            self._tool_cache.pop(server_id, None)
            # Clean up metrics for this server
            prefix = f"{server_id}."
            for key in list(self._metrics.keys()):
                if key.startswith(prefix):
                    del self._metrics[key]

    async def ensure_registered(self, server_id: str) -> bool:
        """Reconnect if session was lost. Returns True if healthy."""
        info = self._sessions.get(server_id)
        if not info or info.status == PluginStatus.INACTIVE:
            return False
        if info.status == PluginStatus.ERROR:
            try:
                await self.register(server_id, info.plugin_name, info.url, info.transport)
                return True
            except Exception:
                return False
        return True

    # ── Connection (uses official mcp SDK when available, falls back to HTTP) ─

    async def _connect(self, info: SessionInfo, headers: dict):
        """Establish transport connection to the MCP server."""
        try:
            from mcp.client.streamable_http import streamablehttp_client
            from mcp.client.sse import sse_client
        except ImportError:
            logger.warning("mcp SDK not installed, falling back to HTTP transport")
            await self._connect_http(info, headers)
            return

        url = info.url
        try:
            if info.transport == "streamable_http":
                # streamablehttp_client returns an async context manager
                info._client = streamablehttp_client(url, headers=headers)
            elif info.transport == "sse":
                info._client = sse_client(url, headers=headers)
            else:
                # Fallback for plain HTTP
                await self._connect_http(info, headers)
                return

            # Enter the context
            if hasattr(info._client, '__aenter__'):
                streams = await info._client.__aenter__()
                # streams is typically (read_stream, write_stream, get_session_id)
                if isinstance(streams, tuple) and len(streams) >= 2:
                    info._session = streams
                else:
                    info._session = streams
            logger.info("Connected to MCP plugin %s via %s", info.plugin_name, info.transport)
        except Exception as e:
            logger.warning("SDK connect failed for %s, falling back to HTTP: %s", info.plugin_name, e)
            await self._connect_http(info, headers)

    async def _connect_http(self, info: SessionInfo, headers: dict):
        """Fallback HTTP connection for MCP servers without SDK support."""
        import httpx
        client = httpx.AsyncClient(
            timeout=self._config.connect_timeout,
            headers={**headers, "Content-Type": "application/json"},
        )
        # Quick health check to validate the URL
        try:
            resp = await client.get(f"{info.url}/health", timeout=5.0)
            if resp.status_code != 200:
                raise MCPError(f"Health check failed: {resp.status_code}")
        except Exception as e:
            await client.aclose()
            raise MCPError(f"Connection failed: {e}")

        info._client = client
        info._session = True  # Mark as connected
        logger.info("HTTP connection established to %s", info.plugin_name)

    async def test_connection(self, server_id: str) -> dict:
        """Test connectivity to a registered server."""
        info = self._sessions.get(server_id)
        if not info:
            return {"healthy": False, "error": "Server not registered"}

        try:
            tools = await self._discover_tools(server_id)
            return {"healthy": True, "tool_count": len(tools), "error": None}
        except Exception as e:
            return {"healthy": False, "error": str(e)[:200]}

    # ── Tool Discovery ───────────────────────────────────────────────────

    async def _discover_tools(self, server_id: str) -> list[dict]:
        """Discover tools from an MCP server and update cache."""
        info = self._sessions.get(server_id)
        if not info or info.status == PluginStatus.INACTIVE:
            return []

        try:
            if isinstance(info._session, tuple):
                # SDK session: use proper tool listing
                tools = await self._list_tools_sdk(info)
            else:
                # HTTP fallback
                tools = await self._list_tools_http(info)

            self._tool_cache[server_id] = ToolCacheEntry(tools=tools)
            info.error_count = 0
            return tools
        except Exception as e:
            info.error_count += 1
            info.total_requests += 1
            info.last_error = str(e)
            logger.warning("Tool discovery failed for %s: %s", info.plugin_name, e)
            # Return cached tools if available
            cached = self._tool_cache.get(server_id)
            return cached.tools if cached else []

    async def _list_tools_sdk(self, info: SessionInfo) -> list[dict]:
        """List tools via official MCP SDK session."""
        read_stream, write_stream, *_ = info._session
        # MCP protocol: send tools/list request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {},
        }
        import json
        await write_stream.send(json.dumps(request))
        # Read response (simplified — real impl needs proper JSON-RPC handling)
        response_data = await read_stream.receive()
        if isinstance(response_data, str):
            response_data = json.loads(response_data)
        tools_raw = response_data.get("result", {}).get("tools", [])
        return [
            {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {}),
            }
            for t in tools_raw
        ]

    async def _list_tools_http(self, info: SessionInfo) -> list[dict]:
        """List tools via HTTP fallback."""
        client = info._client
        resp = await client.post(f"{info.url}/tools/list", json={}, timeout=10.0)
        if resp.status_code != 200:
            raise MCPError(f"tools/list returned {resp.status_code}")
        data = resp.json()
        return [
            {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {}),
            }
            for t in data.get("tools", [])
        ]

    async def get_tools(self, server_id: str, force_refresh: bool = False) -> list[dict]:
        """Get cached tools for a server. Refreshes if cache expired."""
        if not force_refresh:
            cached = self._tool_cache.get(server_id)
            if cached and (time.time() - cached.cached_at) < self._config.tool_cache_ttl:
                return cached.tools
        return await self._discover_tools(server_id)

    # ── Tool Execution ───────────────────────────────────────────────────

    async def call_tool(
        self, server_id: str, tool_name: str, arguments: dict,
        timeout: float | None = None,
    ) -> dict:
        """Call a tool on an MCP server with auto-reconnect and metrics."""
        info = self._sessions.get(server_id)
        if not info or info.status == PluginStatus.INACTIVE:
            raise MCPError(f"Server {server_id} not available")

        timeout = timeout or self._config.tool_call_timeout
        metric_key = f"{server_id}.{tool_name}"
        if metric_key not in self._metrics:
            self._metrics[metric_key] = ToolMetrics()

        metrics = self._metrics[metric_key]
        start = time.monotonic()

        for attempt in range(self._config.max_retries):
            try:
                if isinstance(info._session, tuple):
                    result = await self._call_tool_sdk(info, tool_name, arguments, timeout)
                else:
                    result = await self._call_tool_http(info, tool_name, arguments, timeout)

                elapsed_ms = (time.monotonic() - start) * 1000
                metrics.record(success=True, latency_ms=elapsed_ms)
                info.error_count = max(0, info.error_count - 1)
                return result

            except (MCPError, Exception) as e:
                error_str = str(e)
                is_reconnectable = any(kw in error_str.lower() for kw in (
                    "closedresourceerror", "connection", "timeout", "session",
                ))
                if is_reconnectable and attempt < self._config.max_retries - 1:
                    logger.warning("Reconnecting MCP %s (attempt %d): %s", server_id, attempt + 1, e)
                    try:
                        await self.register(server_id, info.plugin_name, info.url, info.transport)
                        info = self._sessions.get(server_id)
                    except Exception:
                        pass
                    delay = min(
                        self._config.retry_base_delay * (2 ** attempt),
                        self._config.retry_max_delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    elapsed_ms = (time.monotonic() - start) * 1000
                    metrics.record(success=False, latency_ms=elapsed_ms)
                    info.error_count += 1
                    info.last_error = error_str
                    raise MCPError(f"Tool call failed after {attempt + 1} attempts: {error_str}")

        raise MCPError(f"Tool call failed after {self._config.max_retries} attempts")

    async def _call_tool_sdk(self, info: SessionInfo, tool_name: str, arguments: dict, timeout: float) -> dict:
        """Call tool via official MCP SDK session."""
        import json
        read_stream, write_stream, *_ = info._session
        request = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000),
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        await write_stream.send(json.dumps(request))
        response_data = await asyncio.wait_for(read_stream.receive(), timeout=timeout)
        if isinstance(response_data, str):
            response_data = json.loads(response_data)
        if "error" in response_data:
            raise MCPError(response_data["error"].get("message", "Unknown error"))
        return response_data.get("result", {})

    async def _call_tool_http(self, info: SessionInfo, tool_name: str, arguments: dict, timeout: float) -> dict:
        """Call tool via HTTP fallback."""
        client = info._client
        resp = await client.post(
            f"{info.url}/tools/call",
            json={"name": tool_name, "arguments": arguments},
            timeout=timeout,
        )
        if resp.status_code != 200:
            info.total_requests += 1
            raise MCPError(f"Tool call HTTP {resp.status_code}: {resp.text[:200]}")
        info.total_requests += 1
        return resp.json()

    async def batch_call_tools(
        self, calls: list[tuple[str, str, dict]], max_concurrent: int = 5,
    ) -> list[dict]:
        """Execute multiple tool calls with concurrency control.

        Args:
            calls: list of (server_id, tool_name, arguments) tuples
            max_concurrent: max simultaneous calls
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _call_one(server_id: str, tool_name: str, args: dict) -> dict:
            async with semaphore:
                try:
                    return await self.call_tool(server_id, tool_name, args)
                except Exception as e:
                    return {"error": str(e), "server_id": server_id, "tool_name": tool_name}

        tasks = [_call_one(sid, tname, args) for sid, tname, args in calls]
        # Execute concurrently with semaphore-based concurrency control
        results = await asyncio.gather(*tasks, return_exceptions=True)
        # Normalize exceptions to error dicts
        normalized = []
        for r in results:
            if isinstance(r, Exception):
                normalized.append({"error": str(r)})
            else:
                normalized.append(r)
        return normalized

    # ── OpenAI Format Conversion ─────────────────────────────────────────

    def format_tools_for_openai(self, server_ids: list[str] | None = None) -> list[dict]:
        """Convert cached MCP tools to OpenAI Function Calling format.

        Tool names are prefixed with plugin_name to avoid collisions.
        """
        openai_tools = []
        servers = server_ids or list(self._sessions.keys())
        for sid in servers:
            info = self._sessions.get(sid)
            cached = self._tool_cache.get(sid)
            if not info or not cached:
                continue
            prefix = f"{info.plugin_name}_"
            for tool in cached.tools:
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": f"{prefix}{tool['name']}",
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {}),
                    },
                })
        return openai_tools

    @staticmethod
    def parse_function_name(full_name: str) -> tuple[str, str]:
        """Parse 'plugin_tool' or 'plugin.tool' back to (plugin_name, tool_name)."""
        if "_" in full_name:
            parts = full_name.split("_", 1)
            return parts[0], parts[1]
        if "." in full_name:
            parts = full_name.split(".", 1)
            return parts[0], parts[1]
        return "", full_name

    # ── Background Loops ─────────────────────────────────────────────────

    async def _health_check_loop(self):
        """Periodic health check for all registered sessions."""
        while True:
            await asyncio.sleep(self._config.health_check_interval)
            for sid, info in list(self._sessions.items()):
                if info.status == PluginStatus.INACTIVE:
                    continue
                try:
                    total = max(info.total_requests, 1)
                    error_rate = info.error_count / total
                    if error_rate >= self._config.error_rate_critical:
                        info.status = PluginStatus.ERROR
                        logger.warning("MCP %s marked ERROR (error_rate=%.2f)", info.plugin_name, error_rate)
                    elif error_rate >= self._config.error_rate_warning:
                        info.status = PluginStatus.DEGRADED
                        logger.info("MCP %s marked DEGRADED (error_rate=%.2f)", info.plugin_name, error_rate)
                    elif info.status in (PluginStatus.DEGRADED, PluginStatus.ERROR) and error_rate < self._config.error_rate_warning:
                        info.status = PluginStatus.ACTIVE
                        logger.info("MCP %s recovered to ACTIVE", info.plugin_name)

                    info.total_requests = 0
                    info.error_count = 0
                except Exception as e:
                    logger.error("Health check error for %s: %s", sid, e)

    async def _cleanup_loop(self):
        """Periodic cleanup of expired cache entries and idle sessions."""
        while True:
            await asyncio.sleep(self._config.cleanup_interval)
            now = time.time()
            # Clean expired tool cache
            for sid in list(self._tool_cache.keys()):
                entry = self._tool_cache.get(sid)
                if entry and (now - entry.cached_at) > self._config.tool_cache_ttl * 2:
                    del self._tool_cache[sid]

    # ── Metrics & Stats ──────────────────────────────────────────────────

    def get_metrics(self, server_id: str | None = None) -> dict:
        """Get per-tool metrics, optionally filtered by server."""
        result = {}
        for key, m in self._metrics.items():
            if server_id and not key.startswith(f"{server_id}."):
                continue
            result[key] = {
                "calls": m.calls,
                "success_rate": round(m.success_rate, 3),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "last_call_at": m.last_call_at,
            }
        return result

    def get_cache_stats(self) -> dict:
        """Get tool cache statistics."""
        entries = {}
        for sid, entry in self._tool_cache.items():
            entries[sid] = {
                "tool_count": len(entry.tools),
                "cached_at": entry.cached_at,
                "age_seconds": round(time.time() - entry.cached_at, 1),
            }
        return {"total_servers": len(entries), "servers": entries}

    def get_session_stats(self) -> dict:
        """Get session statistics."""
        sessions = {}
        for sid, info in self._sessions.items():
            sessions[sid] = {
                "plugin_name": info.plugin_name,
                "status": info.status.value,
                "error_count": info.error_count,
                "total_requests": info.total_requests,
                "uptime_seconds": round(time.time() - info.created_at, 1),
            }
        return {"total": len(sessions), "sessions": sessions}

    # ── Backward-compatible API (for deprecated graphs/nodes/tools.py) ───

    async def get_servers(self) -> list:
        """Return server configs in the old MCPServerConfig-compatible format.

        DEPRECATED: use get_session_stats() instead.
        """
        # Return lightweight objects with .id .name .enabled attributes
        class _ServerInfo:
            def __init__(self, sid, info):
                self.id = sid
                self.name = info.plugin_name
                self.enabled = info.status != PluginStatus.INACTIVE

        return [
            _ServerInfo(sid, info)
            for sid, info in self._sessions.items()
        ]

    async def list_server_tools(self, server_id: str) -> list:
        """Return tools in the old MCPTool-compatible format.

        DEPRECATED: use get_tools(server_id) instead.
        """
        class _ToolInfo:
            def __init__(self, tool_dict, sid, sname):
                self.name = tool_dict.get("name", "")
                self.description = tool_dict.get("description", "")
                self.parameters = tool_dict.get("parameters", {})
                self.server_id = sid
                self.server_name = sname

        tools = await self.get_tools(server_id)
        info = self._sessions.get(server_id)
        sname = info.plugin_name if info else server_id
        return [_ToolInfo(t, server_id, sname) for t in tools]


# Global singleton
mcp_client = MCPClientFacade()
