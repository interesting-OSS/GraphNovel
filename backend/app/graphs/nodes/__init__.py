"""Reusable LangGraph nodes for the novel creation platform.

AgentNode     — wraps any BaseAgent with streaming, retry, and state update.
                Set enable_mcp_tools=True for dynamic MCP tool-calling.
RetrievalNode — RAG retrieval and context injection.

(ToolNode is deprecated — use AgentNode(enable_mcp_tools=True) instead.)
"""

from app.graphs.nodes.agents import AgentNode
from app.graphs.nodes.retrieval import RetrievalNode

__all__ = ["AgentNode", "RetrievalNode"]
