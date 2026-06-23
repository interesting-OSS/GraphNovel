"""MCP Tool Adapter — bridge between MCP-registered tools and LangChain function-calling.

Converts MCP tools (discovered from user-registered MCP servers) into LangChain
StructuredTool instances, then provides a tool-calling loop where the LLM
autonomously decides which tools to invoke.

Usage:
    from app.graphs.mcp_tool_adapter import get_available_mcp_tools, run_tool_calling_loop

    tools = await get_available_mcp_tools()
    answer = await run_tool_calling_loop(model, system_prompt, user_prompt, tools)
"""
from __future__ import annotations
import json
import logging
from typing import Optional, Any
from pydantic import BaseModel, Field, create_model
from langchain_core.tools import StructuredTool
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.language_models import BaseChatModel

from app.mcp.server_manager import mcp_manager

logger = logging.getLogger(__name__)

# ── JSON Schema → Pydantic ────────────────────────────────────────────────

_JSON_TYPE_MAP: dict[str, type] = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _json_schema_to_pydantic(schema: dict, model_name: str) -> Optional[type[BaseModel]]:
    """Convert a JSON Schema 'properties' block into a Pydantic model.

    Returns None if the schema is empty or conversion fails, so the caller
    can fall back to a plain-function StructuredTool without args_schema.
    """
    properties = schema.get("properties", {})
    if not properties:
        return None

    required: set[str] = set(schema.get("required", []))
    fields: dict[str, tuple[type, Any]] = {}

    try:
        for name, prop in properties.items():
            json_type = prop.get("type", "string")
            field_type = _JSON_TYPE_MAP.get(json_type, str)

            # Handle enum constraints via Literal
            if prop.get("enum"):
                from typing import Literal
                field_type = Literal[tuple(prop["enum"])]  # type: ignore[valid-type]

            is_required = name in required
            field_kwargs: dict = {"description": prop.get("description", "")}
            if is_required:
                field_kwargs["default"] = ...
            else:
                field_kwargs["default"] = prop.get("default", None)

            fields[name] = (field_type, Field(**field_kwargs))

        return create_model(model_name, **fields)  # type: ignore[call-overload]

    except Exception as exc:
        logger.debug("Failed to create Pydantic model for '%s': %s", model_name, exc)
        return None


# ── MCP Tool → LangChain StructuredTool ────────────────────────────────────


async def _execute_mcp_tool(server_id: str, tool_name: str, **kwargs: Any) -> str:
    """Execute an MCP tool and return its result as a string."""
    try:
        result = await mcp_manager.call_tool(server_id, tool_name, kwargs)
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.warning("MCP tool '%s' on server '%s' failed: %s", tool_name, server_id, exc)
        return f"Tool execution error: {exc}"


def _mcp_tool_to_langchain(tool_dict: dict) -> Optional[StructuredTool]:
    """Wrap one MCP tool dict as a LangChain StructuredTool.

    Args:
        tool_dict: dict from mcp_service.list_all_tools(), with keys:
                   name, description, parameters, server_id, server_name

    Returns:
        StructuredTool or None if construction fails.
    """
    tool_name: str = tool_dict.get("name", "")
    description: str = tool_dict.get("description", "") or f"MCP tool: {tool_name}"
    parameters: dict = tool_dict.get("parameters", {})
    server_id: str = tool_dict.get("server_id", "")
    server_name: str = tool_dict.get("server_name", "")

    full_description = description
    if server_name:
        full_description = f"[{server_name}] {description}"

    # Build args_schema from JSON Schema if available
    args_schema: Optional[type[BaseModel]] = None
    if parameters and parameters.get("properties"):
        args_schema = _json_schema_to_pydantic(
            parameters, f"{tool_name}_args"
        )

    try:
        if args_schema is not None:
            # With schema: the tool accepts validated keyword arguments
            async def _structured_fn(**kwargs: Any) -> str:
                return await _execute_mcp_tool(server_id, tool_name, **kwargs)

            return StructuredTool.from_function(
                name=tool_name,
                description=full_description,
                args_schema=args_schema,
                coroutine=_structured_fn,
            )
        else:
            # Without schema: accept any kwargs as a raw dict
            async def _raw_fn(**kwargs: Any) -> str:
                return await _execute_mcp_tool(server_id, tool_name, **kwargs)

            return StructuredTool.from_function(
                name=tool_name,
                description=full_description,
                coroutine=_raw_fn,
            )
    except Exception as exc:
        logger.warning("Failed to wrap MCP tool '%s' as StructuredTool: %s", tool_name, exc)
        return None


# ── Tool Discovery ─────────────────────────────────────────────────────────


async def get_available_mcp_tools() -> list[StructuredTool]:
    """Fetch all enabled MCP tools and convert them to LangChain StructuredTool instances.

    Tools from unreachable servers are silently skipped.
    """
    from app.services.mcp_service import mcp_service

    langchain_tools: list[StructuredTool] = []
    try:
        all_tools = await mcp_service.list_all_tools()
    except Exception as exc:
        logger.warning("Failed to list MCP tools: %s", exc)
        return langchain_tools

    for tool_dict in all_tools:
        lc_tool = _mcp_tool_to_langchain(tool_dict)
        if lc_tool is not None:
            langchain_tools.append(lc_tool)

    logger.info("Loaded %d MCP tools as LangChain StructuredTools", len(langchain_tools))
    return langchain_tools


# ── Tool-Calling Loop ──────────────────────────────────────────────────────


async def run_tool_calling_loop(
    model: BaseChatModel,
    system_prompt: str,
    user_prompt: str,
    tools: list[StructuredTool],
    max_iterations: int = 10,
) -> str:
    """Execute the LLM ⟷ tool loop until the model produces a final answer.

    Flow:
        1. Bind tools to model, invoke with [SystemMessage, HumanMessage]
        2. If response has tool_calls → execute each tool → append ToolMessage → loop
        3. If response has no tool_calls → return response.content (final answer)
        4. Safety limit: max_iterations (default 10)

    Args:
        model: LangChain BaseChatModel instance.
        system_prompt: System instruction for the LLM.
        user_prompt: User query / task description.
        tools: List of StructuredTool instances to make available.
        max_iterations: Maximum tool-calling round-trips before forced return.

    Returns:
        The final text response from the model.
    """
    tool_map: dict[str, StructuredTool] = {t.name: t for t in tools}
    model_with_tools = model.bind_tools(tools)

    messages: list = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    for iteration in range(max_iterations):
        # ── Invoke model with accumulated messages ──
        try:
            response = await model_with_tools.ainvoke(messages)
        except Exception as exc:
            logger.error("Model invocation failed at iteration %d: %s", iteration, exc)
            break

        # AIMessage may be returned as a dict in some LangChain versions
        if isinstance(response, dict):
            response = AIMessage(**response)

        messages.append(response)

        # ── No tool_calls → final answer ──
        tool_calls = getattr(response, "tool_calls", None)
        if not tool_calls:
            content = getattr(response, "content", "")
            return content if isinstance(content, str) else str(content)

        # ── Execute each tool call ──
        for tc in tool_calls:
            tc_name = tc.get("name", "") if isinstance(tc, dict) else getattr(tc, "name", "")
            tc_id = tc.get("id", "") if isinstance(tc, dict) else getattr(tc, "id", "")
            tc_args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})

            tool = tool_map.get(tc_name)
            if tool is None:
                messages.append(ToolMessage(
                    content=f"Error: no tool named '{tc_name}' is available.",
                    tool_call_id=tc_id,
                ))
                logger.warning("Model requested unknown tool: %s", tc_name)
                continue

            try:
                result = await tool.ainvoke(tc_args)
                result_str = result if isinstance(result, str) else json.dumps(
                    result, ensure_ascii=False, default=str
                )
            except Exception as exc:
                result_str = f"Tool '{tc_name}' execution failed: {exc}"
                logger.warning("Tool execution failed: %s", exc)

            messages.append(ToolMessage(content=result_str, tool_call_id=tc_id))

    # ── Exhausted iterations ──
    logger.warning("Tool-calling loop exhausted after %d iterations", max_iterations)
    if messages:
        last = messages[-1]
        content = getattr(last, "content", "")
        return content if isinstance(content, str) else str(content)
    return ""
