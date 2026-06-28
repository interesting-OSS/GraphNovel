"""InspirationSubGraph — AI-driven creative inspiration generation."""
from typing import Literal
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)


from app.graphs.utils import get_ai_service as _get_ai_service


async def generate_options(state: NovelState) -> dict:
    """Generate creative inspiration options based on genre and context."""
    ai = _get_ai_service(state, temperature=0.9, max_tokens=8000)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    description = state.get("description", "")
    world = state.get("world_setting", {})
    characters = state.get("characters", [])
    feedback = state.get("human_feedback", "")

    char_summary = ", ".join(c.get("name", "") for c in characters[:5]) if characters else "暂无角色"
    world_summary = ""
    for key in ["time_period", "power_system", "factions"]:
        val = world.get(key, "")
        if val:
            world_summary += f"{val[:100]} "

    refine_hint = f"\n用户要求调整方向：{feedback}" if feedback else ""

    prompt = f"""你是一位创意写作顾问。请为以下小说项目提供创意灵感：

小说标题：{title}
类型：{genre}
简介：{description}
世界观：{world_summary}
现有角色：{char_summary}
{refine_hint}

请以JSON数组格式输出3-5个创意点子：
```json
[
  {{
    "id": "insp_1",
    "idea": "创意点子描述（50-200字）",
    "type": "情节转折/角色发展/世界观扩展/冲突设计/悬念设置",
    "genre_tags": ["标签1", "标签2"],
    "impact": "high/medium/low",
    "implementation": "如何在实际写作中应用这个点子"
  }}
]
```
只输出JSON数组。"""

    try:
        result = await ai.generate_json("你是一位富有创造力的小说顾问。只输出JSON数组。", prompt)
        if isinstance(result, dict):
            result = [result]
        inspirations = state.get("inspirations", [])
        for insp in result:
            import uuid
            insp.setdefault("id", str(uuid.uuid4()))
        inspirations.extend(result)
        return {"inspirations": inspirations, "current_phase": "options_generated",
                "human_feedback": None}
    except Exception as e:
        logger.error("generate_options failed: %s", e)
        return {"current_phase": "options_generated", "error": str(e)}


async def refine_iteration(state: NovelState) -> dict:
    """Refine inspiration based on user feedback."""
    ai = _get_ai_service(state, temperature=0.9, max_tokens=8000)
    feedback = state.get("human_feedback", "")

    if not feedback:
        return {"current_phase": "refined"}

    prompt = f"""用户对之前的灵感方向提出了反馈："{feedback}"

请根据这个反馈重新生成3个更符合用户预期的创意点子，以JSON数组格式输出：
```json
[
  {{
    "id": "insp_r1",
    "idea": "改进后的创意点子",
    "type": "情节转折/角色发展/世界观扩展/冲突设计/悬念设置",
    "genre_tags": ["标签"],
    "impact": "high/medium/low",
    "implementation": "如何实现"
  }}
]
```
只输出JSON数组。"""

    try:
        result = await ai.generate_json("你是一位创意写作顾问。只输出JSON数组。", prompt)
        if isinstance(result, dict):
            result = [result]
        inspirations = state.get("inspirations", [])
        for insp in result:
            import uuid
            insp.setdefault("id", str(uuid.uuid4()))
        inspirations.extend(result)
        return {"inspirations": inspirations, "current_phase": "refined", "human_feedback": None}
    except Exception as e:
        logger.error("refine_iteration failed: %s", e)
        return {"current_phase": "refined", "error": str(e)}


def route_refine(state: NovelState) -> Literal["done", "refine"]:
    """Decide if the user wants more refinement."""
    feedback = state.get("human_feedback", "")
    if feedback == "refine":
        return "refine"
    return "done"


def create_inspiration_subgraph():
    """Create the Inspiration Generation subgraph.

    Flow: generate_options → [user feedback] → refine_iteration (loop) or done
    """
    builder = StateGraph(NovelState)

    builder.add_node("generate_options", generate_options)
    builder.add_node("refine_iteration", refine_iteration)

    builder.set_entry_point("generate_options")
    builder.add_conditional_edges(
        "generate_options",
        route_refine,
        {"done": END, "refine": "refine_iteration"}
    )
    builder.add_edge("refine_iteration", "generate_options")

    return builder.compile()
