"""Shared utilities for graph nodes and subgraphs.

Provides a single get_ai_service() to replace the 11 duplicated copies
that previously existed across main_graph.py and every subgraph.
"""

from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.config import settings


def get_gen_config(data: dict, **overrides) -> dict:
    """Build generation_config from saved settings, with optional request overrides.

    Tries frontend field names (ai_provider/ai_model/ai_api_key) first,
    then falls back to short names (provider/model/api_key), then to settings defaults.
    """
    provider = (
        data.get("ai_provider")
        or data.get("provider")
        or settings.default_llm_provider
    )
    provider_cfg = settings.get_provider_config(provider)
    return {
        "provider": provider,
        "model": (
            data.get("ai_model")
            or data.get("model")
            or settings.default_llm_model
        ),
        "api_key": (
            data.get("ai_api_key")
            or data.get("api_key")
            or provider_cfg.get("api_key")
        ),
        "base_url": (
            data.get("ai_base_url")
            or data.get("base_url")
            or provider_cfg.get("base_url")
        ),
        "temperature": data.get("temperature", 0.7),
        "max_tokens": data.get("max_tokens", 32000),
        **overrides,
    }


def get_ai_service(state: NovelState, **overrides):
    """Create an AIService instance from the state's generation_config.

    Caller can override any parameter via kwargs.  The overrides dict
    is consumed (popped) so we never forward unknown keys to create_ai_service.
    """
    config = state.get("generation_config", {})
    return create_ai_service(
        provider=overrides.pop("provider", config.get("provider", "openai")),
        api_key=overrides.pop("api_key", config.get("api_key", None)),
        base_url=overrides.pop("base_url", config.get("base_url", None)),
        model=overrides.pop("model", config.get("model", settings.default_llm_model)),
        temperature=overrides.pop("temperature", config.get("temperature", 0.7)),
        max_tokens=overrides.pop("max_tokens", config.get("max_tokens", 32000)),
        **overrides,
    )
