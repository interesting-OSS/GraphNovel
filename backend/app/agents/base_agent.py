"""Base agent class for all specialized agents."""
from typing import Optional, AsyncGenerator
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage


class BaseAgent:
    """Base class for all novel creation agents.

    Each specialized agent inherits from this and overrides:
    - system_prompt: The system instructions for the agent
    - role_name: Human-readable name for logging/display
    """

    role_name: str = "Base Agent"
    system_prompt: str = "You are a helpful AI assistant."

    def __init__(self, model: Optional[BaseChatModel] = None):
        self.model = model

    def set_model(self, model: BaseChatModel):
        """Set or update the LLM model for this agent."""
        self.model = model

    def _build_messages(self, user_prompt: str) -> list:
        """Build the message list for an LLM call."""
        return [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=user_prompt),
        ]

    async def generate(self, user_prompt: str) -> str:
        """Generate a non-streaming response."""
        if not self.model:
            raise RuntimeError(f"{self.role_name}: No model configured")
        messages = self._build_messages(user_prompt)
        response = await self.model.ainvoke(messages)
        return response.content

    async def generate_stream(self, user_prompt: str) -> AsyncGenerator[str, None]:
        """Generate a streaming response, yielding content chunks."""
        if not self.model:
            raise RuntimeError(f"{self.role_name}: No model configured")
        messages = self._build_messages(user_prompt)
        async for chunk in self.model.astream(messages):
            content = chunk.content
            if content:
                yield content
