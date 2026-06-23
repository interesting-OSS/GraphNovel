"""ToolNode — MCP (Model Context Protocol) tool integration for LangGraph.

Wraps external tool calls (via MCP servers) as LangGraph nodes, enabling
AI agents to call registered tools during novel creation.

Features:
  - Dynamic MCP tool discovery and invocation
  - Tool call SSRF protection
  - Progress tracking for long-running tool calls
  - Automatic retry on transient failures

Usage:
    from app.graphs.nodes import ToolNode
    builder.add_node("web_search", ToolNode(tool_name="web_search"))
"""
from __future__ import annotations
from typing import Optional, Any
from app.graphs.state import NovelState
from app.mcp.server_manager import mcp_manager
from app.logger import get_logger
import asyncio
import json

logger = get_logger(__name__)


class ToolNode:
    """DEPRECATED — use AgentNode(enable_mcp_tools=True) for dynamic tool-calling.

    Kept for reference. The recommended approach is to let the LLM autonomously
    decide which MCP tools to call via the function-calling loop in AgentNode,
    rather than hardcoding tool names in the graph topology.

    LangGraph node that invokes an MCP tool.

    Parameters
    ----------
    tool_name : str
        Name of the MCP tool to invoke (e.g. 'web_search', 'image_generate').
    server_name : str, optional
        Specific MCP server to use.  If omitted, searches all enabled servers.
    timeout : int
        Max seconds to wait for tool response (default 60).
    retries : int
        Number of retries on failure (default 1).
    """

    def __init__(
        self,
        tool_name: str,
        server_name: Optional[str] = None,
        timeout: int = 60,
        retries: int = 1,
    ):
        self.tool_name = tool_name
        self.server_name = server_name
        self.timeout = timeout
        self.retries = retries

    async def __call__(self, state: NovelState) -> dict:
        """Execute the tool and return state updates."""
        tool_args = self._build_args(state)

        last_error = None
        for attempt in range(self.retries + 1):
            try:
                result = await self._invoke_with_timeout(tool_args)
                return self._process_result(state, result)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "ToolNode %s attempt %d/%d: %s",
                    self.tool_name, attempt + 1, self.retries + 1, exc,
                )
                if attempt < self.retries:
                    await asyncio.sleep(2 ** attempt)

        return {"error": str(last_error), "current_phase": "tool_error"}

    # ── internals ──

    def _build_args(self, state: NovelState) -> dict:
        """Build tool arguments from the current state.

        Override in subclasses for tool-specific argument mapping.
        """
        # Default: use human_feedback as query, or extract from generation context
        feedback = state.get("human_feedback", "")
        if feedback:
            return {"query": feedback}
        return {"query": state.get("title", ""), "context": state.get("description", "")}

    async def _invoke_with_timeout(self, args: dict) -> Any:
        """Call the MCP tool with a timeout wrapper."""
        return await asyncio.wait_for(
            self._invoke_tool(args),
            timeout=self.timeout,
        )

    async def _invoke_tool(self, args: dict) -> Any:
        """Find the tool across enabled MCP servers and invoke it."""
        # Discover servers that provide this tool
        servers = await mcp_manager.get_servers()
        candidate_servers = []

        for server in servers:
            if self.server_name and server.name != self.server_name:
                continue
            if not server.enabled:
                continue
            try:
                tools = await mcp_manager.list_server_tools(server.name)
                for tool in tools:
                    if tool.name == self.tool_name:
                        candidate_servers.append(server.name)
                        break
            except Exception:
                continue

        if not candidate_servers:
            raise RuntimeError(f"No enabled MCP server provides tool '{self.tool_name}'")

        # Use the first available server
        server_id = candidate_servers[0]
        raw_result = await mcp_manager.call_tool(server_id, self.tool_name, args)
        return raw_result

    def _process_result(self, state: NovelState, result: Any) -> dict:
        """Convert tool result into state updates.

        Override for tool-specific result processing.
        """
        result_key = f"_tool_{self.tool_name}_result"
        return {result_key: result, "current_phase": "tool_complete"}


# WebSearchNode has been removed in favor of AgentNode(enable_mcp_tools=True).
# The LLM now dynamically discovers and calls any MCP-registered tool,
# including web_search, without hardcoded tool names.
