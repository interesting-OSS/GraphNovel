"""Unified AI service — multi-provider LLM with streaming, tools, retry, and multimodal.

Supported providers:
  - openai / deepseek : OpenAI-compatible text models
  - qwen              : Qwen multimodal (DashScope, OpenAI-compatible) — text + image
  - kimi              : Moonshot Kimi (OpenAI-compatible)
  - anthropic         : Anthropic Claude
  - gemini            : Google Gemini

Qwen is special: it can generate images (qwen-vl-max) and understand images.
For image generation, use generate_image().
"""
from typing import Optional, AsyncGenerator, Any
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
import json
import asyncio
import logging
import base64

logger = logging.getLogger(__name__)

# OpenAI-compatible providers (use ChatOpenAI with custom base_url)
_OPENAI_COMPATIBLE = {"openai", "deepseek", "qwen", "kimi"}

# Providers that support multimodal (image input/output)
_MULTIMODAL_PROVIDERS = {"qwen"}

# Model lists per provider
PROVIDER_MODELS = {
    "openai":    ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o1-preview", "o1-mini"],
    "deepseek":  ["deepseek-chat", "deepseek-reasoner", "deepseek-v3"],
    "qwen":      ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-vl-max", "qwen-vl-plus"],
    "kimi":      ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k", "kimi-latest"],
    "anthropic": ["claude-sonnet-4-6", "claude-opus-4-7", "claude-haiku-4-5"],
    "gemini":    ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
}

DEFAULT_BASE_URLS = {
    "deepseek": "https://api.deepseek.com/v1",
    "qwen":     "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "kimi":     "https://api.moonshot.cn/v1",
}


class AIService:
    """Unified AI calling layer.

    Features:
      - Multi-provider: openai/deepseek/qwen/kimi/anthropic/gemini
      - Qwen multimodal: image generation via dashscope ImageGeneration API
      - SSE streaming with token-level granularity
      - JSON extraction with retry
      - Provider auto-detection via settings
    """

    def __init__(
        self,
        provider: str = "openai",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 32000,
    ):
        # Resolve actual provider name
        raw_provider = (provider or settings.default_ai_provider).lower().strip()
        self.provider = raw_provider
        self.api_key = api_key
        self.base_url = base_url or DEFAULT_BASE_URLS.get(raw_provider)
        self.model_name = model or settings.default_ai_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._model: Optional[BaseChatModel] = None
        self._is_multimodal = raw_provider in _MULTIMODAL_PROVIDERS

    @property
    def is_multimodal(self) -> bool:
        return self._is_multimodal

    @property
    def model(self) -> BaseChatModel:
        """Public access to the underlying chat model."""
        return self._get_model()

    def _resolve_auth(self) -> tuple[str, str]:
        """Get resolved (api_key, base_url) for this provider."""
        cfg = settings.get_provider_config(self.provider)
        key = self.api_key or cfg["api_key"]
        url = self.base_url or cfg["base_url"] or DEFAULT_BASE_URLS.get(self.provider, "")
        if not key:
            raise ValueError(
                f"No API key configured for provider '{self.provider}'. "
                f"Set {self.provider.upper()}_API_KEY in .env or pass api_key=."
            )
        return key, url

    def _get_model(self) -> BaseChatModel:
        """Lazy-initialize the appropriate chat model."""
        if self._model is not None:
            return self._model

        api_key, base_url = self._resolve_auth()

        if self.provider in _OPENAI_COMPATIBLE:
            kwargs = {
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "api_key": api_key,
            }
            if base_url:
                kwargs["base_url"] = base_url
            self._model = ChatOpenAI(**kwargs)

        elif self.provider == "anthropic":
            kwargs = {
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "api_key": api_key,
            }
            if self.base_url:
                kwargs["base_url"] = self.base_url
            self._model = ChatAnthropic(**kwargs)

        elif self.provider == "gemini":
            kwargs = {
                "model": self.model_name,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "google_api_key": api_key,
            }
            self._model = ChatGoogleGenerativeAI(**kwargs)

        else:
            # Fallback: try as OpenAI-compatible
            kwargs = {
                "model": self.model_name or "gpt-4o",
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "api_key": api_key,
            }
            if base_url:
                kwargs["base_url"] = base_url
            self._model = ChatOpenAI(**kwargs)

        return self._model

    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Non-streaming text generation."""
        model = self._get_model()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        response = await model.ainvoke(messages)
        return response.content

    async def generate_stream(
        self, system_prompt: str, user_prompt: str
    ) -> AsyncGenerator[str, None]:
        """Streaming text generation, yields content chunks."""
        model = self._get_model()
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
        async for chunk in model.astream(messages):
            content = chunk.content
            if content:
                yield content

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
    ) -> dict:
        """Generate and extract JSON with retry + exponential backoff."""
        full_system = system_prompt + "\n请只输出有效的JSON，不要包裹在 markdown 代码块中。"
        last_error = None
        for attempt in range(max_retries):
            try:
                text = await self.generate(full_system, user_prompt)
                text = text.strip()
                # Remove code fences if present
                if text.startswith("```"):
                    lines = text.split("\n")
                    text = "\n".join(lines[1:-1] if len(lines) > 2 and lines[-1].strip() == "```" else lines[1:])
                return json.loads(text)
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        raise ValueError(f"Failed to extract JSON after {max_retries} attempts: {last_error}")

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> dict:
        """Generate an image using Qwen/DashScope multimodal model.

        Qwen image generation uses dashscope ImageGeneration API.
        Returns dict with 'url' (or 'b64_json') and 'revised_prompt'.
        """
        if self.provider == "qwen":
            return await self._generate_image_qwen(prompt, size)
        raise NotImplementedError(f"Image generation not supported for provider '{self.provider}'")

    async def _generate_image_qwen(self, prompt: str, size: str = "1024x1024") -> dict:
        """Call Qwen (DashScope) image generation API.

        Uses the multimodal qwen-vl-max or qwen-turbo model for text-to-image.
        Falls back to the DashScope ImageGeneration endpoint.
        """
        import httpx
        api_key, _ = self._resolve_auth()

        url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "X-DashScope-Async": "enable",
        }
        payload = {
            "model": "wan2.1-t2i-turbo",
            "input": {"prompt": prompt},
            "parameters": {"size": size, "n": 1},
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                # Submit
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                # Handle async polling
                task_id = data.get("output", {}).get("task_id", "")
                if task_id:
                    task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
                    for _ in range(20):  # poll up to 100s
                        await asyncio.sleep(5)
                        task_resp = await client.get(task_url, headers=headers)
                        task_resp.raise_for_status()
                        task_data = task_resp.json()
                        status = task_data.get("output", {}).get("task_status", "")
                        if status == "SUCCEEDED":
                            results = task_data.get("output", {}).get("results", [])
                            if results:
                                return {"url": results[0].get("url", ""), "revised_prompt": prompt}
                        elif status == "FAILED":
                            raise RuntimeError(f"Image generation failed: {task_data}")
                return {"url": "", "revised_prompt": prompt, "error": "No results"}
        except Exception as exc:
            logger.error("Qwen image generation failed: %s", exc)
            raise

    def reset(self):
        """Reset cached model to pick up config changes."""
        self._model = None


def create_ai_service(
    provider: str = "openai",
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 32000,
) -> AIService:
    """Factory function for AIService instances."""
    return AIService(
        provider=provider,
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def get_available_providers() -> list[str]:
    """List all providers that have API keys configured."""
    return list(settings.available_providers)


def get_provider_models(provider: str) -> list[str]:
    """Get available models for a provider."""
    return PROVIDER_MODELS.get(provider, ["default"])
