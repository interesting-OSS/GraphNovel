"""CoverGenSubGraph — AI cover image generation."""
from typing import Literal
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def _get_ai_service(state: NovelState, **overrides):
    config = state.get("generation_config", {})
    return create_ai_service(
        provider=overrides.pop("provider", config.get("provider", "openai")),
        api_key=overrides.pop("api_key", config.get("api_key", None)),
        base_url=overrides.pop("base_url", config.get("base_url", None)),
        model=overrides.pop("model", config.get("model", settings.default_ai_model)),
        temperature=overrides.pop("temperature", config.get("temperature", 0.7)),
        max_tokens=overrides.pop("max_tokens", config.get("max_tokens", 4000)),
        **overrides,
    )


async def generate_prompt(state: NovelState) -> dict:
    """Generate a cover image prompt from the novel's content and world setting."""
    ai = _get_ai_service(state)
    title = state.get("title", "")
    description = state.get("description", "")
    genre = state.get("genre", "玄幻")
    world = state.get("world_setting", {})

    world_summary = ""
    for key in ["time_period", "geography", "power_system", "factions", "culture"]:
        val = world.get(key, "")
        if val:
            world_summary += f"{val[:150]} "

    prompt = f"""请根据以下小说信息，生成一个高质量的小说封面提示词（用于AI图像生成）：

小说标题：{title}
类型：{genre}
简介：{description}
世界观元素：{world_summary}

请生成英文和中文两个版本的提示词，以JSON格式输出：
```json
{{
  "prompt_en": "英文提示词（详细描述画面构图、风格、色调、元素）",
  "prompt_cn": "中文提示词（同上，中文版本）",
  "style": "风格（日系/写实/国风/暗黑/赛博朋克等）",
  "mood": "氛围（神秘/热血/温柔/阴暗等）",
  "color_palette": ["主色调1", "主色调2"]
}}
```
只输出JSON。"""

    try:
        result = await ai.generate_json("你是一位专业的封面设计顾问。只输出JSON。", prompt)
        return {
            "cover_prompt": result.get("prompt_en", ""),
            "current_phase": "prompt_generated",
            "_cover_data": result,
        }
    except Exception as e:
        logger.error("generate_prompt failed: %s", e)
        return {"current_phase": "prompt_generated", "error": str(e)}


async def call_image_model(state: NovelState) -> dict:
    """Call the image generation model to create the cover.

    Actual image generation is handled by the cover service in the API layer.
    This node stores the prompt for the service to use.
    """
    cover_data = state.get("_cover_data", {})
    if not cover_data:
        return {"current_phase": "image_generated"}

    logger.info("Cover prompt ready for image generation: %s", cover_data.get("prompt_en", "")[:100])
    return {"current_phase": "image_generated"}


async def store_prompt(state: NovelState) -> dict:
    """Store the cover prompt for potential regeneration."""
    cover_prompt = state.get("cover_prompt", "")
    cover_data = state.get("_cover_data", {})
    return {
        "cover_prompt": cover_prompt or cover_data.get("prompt_en", ""),
        "current_phase": "prompt_stored",
    }


def route_after_select(state: NovelState) -> Literal["regenerate", "done"]:
    """Allow user to accept or regenerate."""
    feedback = state.get("human_feedback", "")
    if feedback == "regenerate":
        return "regenerate"
    return "done"


def create_cover_gen_subgraph():
    """Create the Cover Generation subgraph.

    Flow: generate_prompt → call_image_model → [user select] → store_prompt or regenerate
    """
    builder = StateGraph(NovelState)

    builder.add_node("generate_prompt", generate_prompt)
    builder.add_node("call_image_model", call_image_model)
    builder.add_node("store_prompt", store_prompt)

    builder.set_entry_point("generate_prompt")
    builder.add_edge("generate_prompt", "call_image_model")
    builder.add_conditional_edges(
        "call_image_model",
        route_after_select,
        {"regenerate": "generate_prompt", "done": "store_prompt"}
    )
    builder.add_edge("store_prompt", END)

    return builder.compile()
