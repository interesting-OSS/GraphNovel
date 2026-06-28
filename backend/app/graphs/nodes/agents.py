"""AgentNode — a reusable LangGraph node that wraps a BaseAgent.

Supports:
  - Streaming token output via astream_events
  - Automatic retry with exponential backoff
  - Skill context injection via SkillLoader
  - Structured JSON output with validation
  - Error state propagation

Usage in a subgraph:
    builder.add_node("write_chapter", AgentNode(writer_agent))
"""
from __future__ import annotations
import time
from typing import Optional, Any, Callable, Awaitable
"""Callable 是一个用来声明一个变量或参数是可以被调用的对象【[参1，参2】返回3】
   Awaitable 是一个异步函数的返回值类型，当一个函数需要接收一个异步函数作为参数，
   那么这个函数的返回值类型就是 Awaitable[Any]。
"""
from app.graphs.state import NovelState
from app.agents.base_agent import BaseAgent
from app.services.ai_service import AIService, create_ai_service
from app.skills.loader import get_skill_loader
from app.config import settings
import logging
import asyncio
import json

logger = logging.getLogger(__name__)


def _record_metrics(project_id: str, node_name: str, phase: str, start_time: float, success: bool, error: str = ""):
    """Record node execution metrics (lazy import to avoid circular deps)."""
    try:
        from app.graphs.metrics import record_node_execution
        record_node_execution(project_id, node_name, phase, start_time, success, error)
    except Exception:
        pass  # metrics should never break the main flow

# Type for a prompt-building callback: (state, agent) → user_prompt
PromptBuilder = Callable[[NovelState, BaseAgent], Awaitable[str]]
# Type for result handler: (state, result_text) → state_update_dict
ResultHandler = Callable[[NovelState, str], Awaitable[dict]]


class AgentNode:
    """A callable LangGraph node that wraps a BaseAgent subclass.

    Parameters
    ----------
    agent : BaseAgent
        The agent instance (e.g. WriterAgent(), EditorAgent()).
    prompt_builder : callable
        async (state, agent) → str.  Builds the user prompt from state.
        If omitted, uses agent.system_prompt directly.
    result_handler : callable, optional
        async (state, result_text) → dict.  Transforms LLM output into state updates.
        If omitted, stores the raw text under ``_agent_result``.
    max_retries : int
        Number of retries on failure (default 2, exponential backoff).
    stream : bool
        If True, uses streaming internally (useful for subgraph streaming at API level).
    inject_skill : bool
        If True, injects the active skill context from state into the system prompt.
    enable_mcp_tools : bool
        If True, dynamically discovers all registered MCP tools and lets the LLM
        call them via function-calling.  Falls back to plain generation when no
        MCP tools are available.
    max_tool_iterations : int
        Safety limit on tool-calling round-trips (default 10).
    """

    def __init__(
        self,
        agent: BaseAgent,
        prompt_builder: Optional[PromptBuilder] = None,
        result_handler: Optional[ResultHandler] = None,
        max_retries: int = 2,
        stream: bool = False,
        inject_skill: bool = True,
        enable_mcp_tools: bool = False,
        max_tool_iterations: int = 10,
    ):
        self.agent = agent
        self._prompt_builder = prompt_builder
        self._result_handler = result_handler
        self.max_retries = max_retries
        self.stream = stream
        self.inject_skill = inject_skill
        self.enable_mcp_tools = enable_mcp_tools
        self.max_tool_iterations = max_tool_iterations
        self._ai_service: Optional[AIService] = None

    async def __call__(self, state: NovelState) -> dict:
        """Execute the agent as a LangGraph node.  Returns state updates."""
        last_error: Optional[Exception] = None
        project_id = state.get("project_id", "unknown")
        phase = state.get("current_phase", "running")
        start_time = None  # set later, but declare now for metrics

        for attempt in range(self.max_retries + 1):
            try:
                self._ensure_ai_service(state)
                system_prompt = self._build_system_prompt(state)
                user_prompt = await self._build_user_prompt(state)

                start_time = time.time()
                if self.enable_mcp_tools:
                    raw = await self._generate_with_tools(system_prompt, user_prompt)
                elif self.stream:
                    raw = ""
                    async for chunk in self._ai_service.generate_stream(system_prompt, user_prompt):
                        raw += chunk
                else:
                    raw = await self._ai_service.generate(system_prompt, user_prompt)

                updates = await self._apply_result(state, raw)
                updates["error"] = None  # clear previous error
                _record_metrics(project_id, self.agent.role_name, phase, start_time, True)
                return updates

            except Exception as exc:
                last_error = exc
                logger.warning(
                    "AgentNode %s attempt %d/%d failed: %s",
                    self.agent.role_name, attempt + 1, self.max_retries + 1, exc,
                )
                if attempt < self.max_retries:
                    await asyncio.sleep(2 ** attempt)

        if start_time is not None:
            _record_metrics(project_id, self.agent.role_name, phase, start_time, False, str(last_error))
        logger.error("AgentNode %s failed after %d retries", self.agent.role_name, self.max_retries + 1)
        return {"error": str(last_error), "current_phase": "agent_error"}

    async def _generate_with_tools(self, system_prompt: str, user_prompt: str) -> str:
        """Discover MCP tools and run the tool-calling loop.

        Falls back to plain generation when no MCP tools are available.
        """
        from app.graphs.mcp_tool_adapter import get_available_mcp_tools, run_tool_calling_loop

        lc_tools = await get_available_mcp_tools()
        if not lc_tools:
            logger.info("No MCP tools available, falling back to plain generation")
            return await self._ai_service.generate(system_prompt, user_prompt)

        model = self._ai_service.model
        return await run_tool_calling_loop(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=lc_tools,
            max_iterations=self.max_tool_iterations,
        )

    # ── internals ──

    def _ensure_ai_service(self, state: NovelState):
        if self._ai_service is None:
            config = state.get("generation_config", {})
            self._ai_service = create_ai_service(
                provider=config.get("provider", "openai"),
                api_key=config.get("api_key"),
                base_url=config.get("base_url"),
                model=config.get("model", settings.default_llm_model),
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 32000),
            )
            self.agent.set_model(self._ai_service.model)

    def _build_system_prompt(self, state: NovelState) -> str:
        base = self.agent.system_prompt
        if self.inject_skill:
            active_skill = state.get("active_skill")
            if active_skill:
                loader = get_skill_loader()
                skill = loader.load(active_skill)
                if skill:
                    base = skill.get_injected_prompt(base)
        return base

    async def _build_user_prompt(self, state: NovelState) -> str:
        if self._prompt_builder:
            return await self._prompt_builder(state, self.agent)
        # Default: format system prompt with state values
        return self.agent.system_prompt

    async def _apply_result(self, state: NovelState, raw: str) -> dict:
        if self._result_handler:
            return await self._result_handler(state, raw)
        return {"_agent_result": raw}


# ── Pre-built prompt builders for common operations ──


async def json_result_handler(state: NovelState, raw: str) -> dict:
    """Extract JSON from agent output and merge into state."""
    try:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        data = json.loads(text)
        if isinstance(data, dict):
            return data
        return {"_json_result": data}
    except json.JSONDecodeError:
        return {"_raw_result": raw, "_parse_error": "Failed to parse JSON from agent output"}
