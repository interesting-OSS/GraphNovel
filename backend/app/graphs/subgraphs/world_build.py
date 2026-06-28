"""WorldBuildSubGraph — structured world setting generation with real AI."""
from typing import Literal
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.graphs.utils import get_ai_service as _get_ai_service
import json
import logging

logger = logging.getLogger(__name__)

WORLD_BUILD_SYSTEM = """你是一位资深的世界观架构师，精通各类小说的世界观设计。

请根据用户的小说设定，按以下维度生成世界观内容。以JSON格式输出，每个字段用中文描述（300-500字）：

```json
{
  "time_period": "时代背景（历史时期、时间跨度、关键历史事件）",
  "geography": "地理版图（地形地貌、重要地点、气候环境）",
  "power_system": "力量体系（修炼/魔法/科技等力量等级和规则）",
  "factions": "势力格局（主要势力、组织关系、权力结构）",
  "culture": "文化风俗（语言、节日、风俗、社会规范）",
  "rules": "世界规则（物理法则、魔法限制、禁忌、特殊设定）"
}
```

要求：
1. 各维度之间保持内部一致性和逻辑自洽
2. 内容需契合小说类型和主题
3. 提供足够的深度让后续创作有据可依
4. 避免陈词滥调，追求新颖独特的设定"""


async def generate_time_period(state: NovelState) -> dict:
    """Generate the time period and historical background."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    description = state.get("description", "")
    existing = state.get("world_setting", {})

    prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}

请生成这部小说的「时代背景」维度设定。要求300-500字，内容详实具体。只输出纯文本，不要JSON格式。"""

    try:
        result = await ai.generate(WORLD_BUILD_SYSTEM, prompt)
        world = existing.copy()
        world["time_period"] = result.strip()
        return {"world_setting": world, "current_phase": "time_period_generated"}
    except Exception as e:
        logger.error("generate_time_period failed: %s", e)
        return {"current_phase": "time_period_generated", "error": str(e)}


async def generate_geography(state: NovelState) -> dict:
    """Generate the geography and map layout."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    description = state.get("description", "")
    world = state.get("world_setting", {})
    time_period = world.get("time_period", "")

    prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}
已生成的「时代背景」：{time_period[:300]}

请根据以上信息生成「地理版图」维度设定。要求300-500字，内容详实具体。只输出纯文本，不要JSON格式。"""

    try:
        result = await ai.generate(WORLD_BUILD_SYSTEM, prompt)
        world["geography"] = result.strip()
        return {"world_setting": world, "current_phase": "geography_generated"}
    except Exception as e:
        logger.error("generate_geography failed: %s", e)
        return {"current_phase": "geography_generated", "error": str(e)}


async def generate_power_system(state: NovelState) -> dict:
    """Generate the power/magic/cultivation system."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    description = state.get("description", "")
    world = state.get("world_setting", {})

    prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}
「时代背景」：{world.get('time_period', '')[:200]}
「地理版图」：{world.get('geography', '')[:200]}

请根据以上信息生成「力量体系」维度设定。要求300-500字，详细描述力量等级、修炼/升级方式、关键能力等。
只输出纯文本，不要JSON格式。"""

    try:
        result = await ai.generate(WORLD_BUILD_SYSTEM, prompt)
        world["power_system"] = result.strip()
        return {"world_setting": world, "current_phase": "power_system_generated"}
    except Exception as e:
        logger.error("generate_power_system failed: %s", e)
        return {"current_phase": "power_system_generated", "error": str(e)}


async def generate_factions(state: NovelState) -> dict:
    """Generate factions, organizations, and power dynamics."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    description = state.get("description", "")
    world = state.get("world_setting", {})

    prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}
「时代背景」：{world.get('time_period', '')[:150]}
「力量体系」：{world.get('power_system', '')[:200]}

请根据以上信息生成「势力格局」维度设定。描述3-5个主要势力/组织及其关系。
要求300-500字。只输出纯文本，不要JSON格式。"""

    try:
        result = await ai.generate(WORLD_BUILD_SYSTEM, prompt)
        world["factions"] = result.strip()
        return {"world_setting": world, "current_phase": "factions_generated"}
    except Exception as e:
        logger.error("generate_factions failed: %s", e)
        return {"current_phase": "factions_generated", "error": str(e)}


async def generate_culture(state: NovelState) -> dict:
    """Generate culture, customs, and social norms."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    description = state.get("description", "")
    world = state.get("world_setting", {})

    prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}
「势力格局」：{world.get('factions', '')[:200]}

请根据以上信息生成「文化风俗」维度设定。包括社会规范、节日、语言特色、习俗等。
要求300-500字。只输出纯文本，不要JSON格式。"""

    try:
        result = await ai.generate(WORLD_BUILD_SYSTEM, prompt)
        world["culture"] = result.strip()
        return {"world_setting": world, "current_phase": "culture_generated"}
    except Exception as e:
        logger.error("generate_culture failed: %s", e)
        return {"current_phase": "culture_generated", "error": str(e)}


MAX_FIX_ATTEMPTS = 3


async def check_consistency(state: NovelState) -> dict:
    """Check the world setting for internal contradictions using AI."""
    ai = _get_ai_service(state)
    world = state.get("world_setting", {})

    if not world:
        return {"current_phase": "consistency_checked"}

    # Don't include internal bookkeeping fields in the check prompt
    checkable = {k: v for k, v in world.items() if not k.startswith("_")}

    prompt = f"""请检查以下世界观设定是否存在内部矛盾或不一致之处：

{json.dumps(checkable, ensure_ascii=False, indent=2)}

请以JSON格式输出：
```json
{{
  "has_conflicts": true/false,
  "conflicts": ["矛盾描述1", "矛盾描述2"],
  "suggestions": ["改进建议1", "改进建议2"]
}}
```"""

    try:
        result = await ai.generate_json(
            system_prompt="你是一位严格的世界观审查员，善于发现设定中的逻辑矛盾。",
            user_prompt=prompt,
            max_retries=3,
        )
        world["consistency_check"] = result

        # Sync to DB if no conflicts (subgraph exits on "done")
        if not result.get("has_conflicts"):
            project_id = state.get("project_id", "")
            if project_id:
                from app.graphs.graph_db_sync import sync_world_setting
                await sync_world_setting(project_id, {
                    k: v for k, v in world.items() if not k.startswith("_")
                })

        return {"world_setting": world, "current_phase": "consistency_checked"}
    except Exception as e:
        logger.error("consistency check failed: %s", e)
        return {"current_phase": "consistency_checked", "error": str(e)}


def route_after_check(state: NovelState) -> Literal["resolve_conflicts", "done"]:
    """Route to resolve_conflicts if inconsistencies found and retries remain."""
    world = state.get("world_setting", {})
    has_conflicts = world.get("consistency_check", {}).get("has_conflicts", False)
    attempts = world.get("_fix_attempts", 0)

    if has_conflicts and attempts < MAX_FIX_ATTEMPTS:
        return "resolve_conflicts"
    return "done"


async def resolve_conflicts(state: NovelState) -> dict:
    """Ask the AI to rewrite conflicting parts of the world setting."""
    ai = _get_ai_service(state)
    world = state.get("world_setting", {})
    check = world.get("consistency_check", {})
    conflicts = check.get("conflicts", [])
    suggestions = check.get("suggestions", [])
    attempts = world.get("_fix_attempts", 0)

    logger.info(
        "Resolving conflicts — attempt %d/%d. Conflicts: %s",
        attempts + 1, MAX_FIX_ATTEMPTS, conflicts,
    )

    # Build a focused prompt: show the current world setting and the problems
    checkable = {k: v for k, v in world.items()
                 if not k.startswith("_") and k != "consistency_check"}

    prompt = f"""当前世界观设定存在以下矛盾，请修改以消除矛盾：

## 当前设定
{json.dumps(checkable, ensure_ascii=False, indent=2)}

## 发现的矛盾
{json.dumps(conflicts, ensure_ascii=False, indent=2)}

## 改进建议
{json.dumps(suggestions, ensure_ascii=False, indent=2)}

请输出修正后的完整世界观设定，以JSON格式输出（只输出需要修改的字段，保留原文中没问题的字段）：
```json
{{
  "time_period": "...",
  "geography": "...",
  "power_system": "...",
  "factions": "...",
  "culture": "..."
}}
```

注意：
1. 只修改存在矛盾的字段，其他字段保持原样
2. 修改后各维度之间必须保持内部一致性
3. 每个字段 300-500 字"""

    try:
        result = await ai.generate_json(
            system_prompt="你是一位资深的世界观架构师，擅长修复世界观设定中的逻辑矛盾。",
            user_prompt=prompt,
            max_retries=3,
        )

        # Merge: only overwrite fields the AI actually returned
        for key in ("time_period", "geography", "power_system", "factions", "culture"):
            if key in result and result[key]:
                world[key] = result[key]

        world["_fix_attempts"] = attempts + 1
        world["_fix_history"] = world.get("_fix_history", []) + [{
            "attempt": attempts + 1,
            "conflicts": conflicts,
            "applied": [k for k in result if k in world and result[k]],
        }]

        # Sync to DB after final fix attempt
        if attempts + 1 >= MAX_FIX_ATTEMPTS:
            project_id = state.get("project_id", "")
            if project_id:
                from app.graphs.graph_db_sync import sync_world_setting
                await sync_world_setting(project_id, {
                    k: v for k, v in world.items() if not k.startswith("_")
                })

        return {"world_setting": world, "current_phase": "conflicts_resolved"}
    except Exception as e:
        logger.error("resolve_conflicts failed: %s", e)
        # Give up on fix attempts if resolution fails
        world["_fix_attempts"] = MAX_FIX_ATTEMPTS
        # Still sync what we have
        project_id = state.get("project_id", "")
        if project_id:
            from app.graphs.graph_db_sync import sync_world_setting
            await sync_world_setting(project_id, {
                k: v for k, v in world.items() if not k.startswith("_")
            })
        return {"world_setting": world, "current_phase": "conflicts_resolved", "error": str(e)}


def route_after_resolve(state: NovelState) -> Literal["check_consistency"]:
    """After resolving conflicts, always loop back to re-check."""
    return "check_consistency"


def create_world_build_subgraph():
    """Create the WorldBuild subgraph.

    Generates world setting dimensions sequentially:
        time_period → geography → power_system → factions → culture
        → consistency_check → [resolve_conflicts → re-check, or done]
        (AI auto-fixes conflicts up to 3 rounds, then exits)
    """
    builder = StateGraph(NovelState)

    builder.add_node("generate_time_period", generate_time_period)
    builder.add_node("generate_geography", generate_geography)
    builder.add_node("generate_power_system", generate_power_system)
    builder.add_node("generate_factions", generate_factions)
    builder.add_node("generate_culture", generate_culture)
    builder.add_node("check_consistency", check_consistency)
    builder.add_node("resolve_conflicts", resolve_conflicts)

    builder.set_entry_point("generate_time_period")
    builder.add_edge("generate_time_period", "generate_geography")
    builder.add_edge("generate_geography", "generate_power_system")
    builder.add_edge("generate_power_system", "generate_factions")
    builder.add_edge("generate_factions", "generate_culture")
    builder.add_edge("generate_culture", "check_consistency")

    # check_consistency → resolve_conflicts (loop) or done (exit)
    builder.add_conditional_edges(
        "check_consistency",
        route_after_check,
        {"resolve_conflicts": "resolve_conflicts", "done": END}
    )

    # resolve_conflicts → back to check_consistency for re-verification
    builder.add_conditional_edges(
        "resolve_conflicts",
        route_after_resolve,
        {"check_consistency": "check_consistency"}
    )

    return builder.compile()
