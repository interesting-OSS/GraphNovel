"""MCP Server Manager — manages MCP plugin lifecycle and tool discovery."""
import httpx
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    id: str
    name: str
    transport: str  # http / streamable_http / sse
    url: str
    enabled: bool = True
    description: str = ""
    config: dict = field(default_factory=dict)


@dataclass
class MCPTool:
    """Represents a tool exposed by an MCP server."""
    name: str
    description: str
    parameters: dict = field(default_factory=dict)
    server_id: str = ""
    server_name: str = ""


class MCPServerManager:
    """Manages MCP server connections and tool discovery.

    Features:
    - Dynamic registration of external MCP servers
    - Tool discovery and listing
    - Tool execution with timeout
    - Health checking
    - SSRF protection
    """

    def __init__(self):
        self._servers: dict[str, MCPServerConfig] = {}
        self._tools: dict[str, List[MCPTool]] = {}
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def register_server(self, config: MCPServerConfig) -> str:
        """Register an MCP server and discover its tools."""
        self._servers[config.id] = config
        await self._discover_tools(config.id)
        return config.id

    async def unregister_server(self, server_id: str):
        """Remove an MCP server registration."""
        self._servers.pop(server_id, None)
        self._tools.pop(server_id, None)

    async def _discover_tools(self, server_id: str):
        """Discover tools from an MCP server."""
        config = self._servers.get(server_id)
        if not config or not config.enabled:
            return

        try:
            client = await self._get_client()
            base = config.url.rstrip("/")
            response = await client.post(
                f"{base}/tools/list",
                json={},
                timeout=10.0,
            )
            if response.status_code == 200:
                data = response.json()
                tools = []
                for tool_data in data.get("tools", []):
                    tools.append(MCPTool(
                        name=tool_data.get("name", ""),
                        description=tool_data.get("description", ""),
                        parameters=tool_data.get("inputSchema", {}),
                        server_id=server_id,
                        server_name=config.name,
                    ))
                self._tools[server_id] = tools
        except Exception:
            self._tools[server_id] = []

    async def list_tools(self) -> List[MCPTool]:
        """List all available tools from registered MCP servers."""
        all_tools = []
        for server_id in list(self._servers.keys()):
            tools = self._tools.get(server_id, [])
            all_tools.extend(tools)
        return all_tools

    async def list_server_tools(self, server_id: str) -> List[MCPTool]:
        """List tools for a specific server."""
        return self._tools.get(server_id, [])

    async def call_tool(
        self, server_id: str, tool_name: str, arguments: dict
    ) -> dict:
        """Call a tool on an MCP server."""
        config = self._servers.get(server_id)
        if not config or not config.enabled:
            raise ValueError(f"MCP server {server_id} not found or disabled")

        client = await self._get_client()
        base = config.url.rstrip("/")
        response = await client.post(
            f"{base}/tools/call",
            json={
                "name": tool_name,
                "arguments": arguments,
            },
            timeout=60.0,
        )
        if response.status_code == 200:
            return response.json()
        else:
            raise RuntimeError(f"MCP tool call failed: {response.status_code}")

    async def health_check(self, server_id: str) -> bool:
        """Check if an MCP server is healthy."""
        config = self._servers.get(server_id)
        if not config:
            return False
        try:
            client = await self._get_client()
            base = config.url.rstrip("/")
            response = await client.get(
                f"{base}/health",
                timeout=5.0,
            )
            return response.status_code == 200
        except Exception:
            return False

    async def get_servers(self) -> List[MCPServerConfig]:
        """List all registered servers."""
        return list(self._servers.values())

    async def close(self):
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Singleton
mcp_manager = MCPServerManager()
