"""CharCreateSubGraph — character creation with real AI generation."""
from typing import Literal
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)

CHAR_GEN_SYSTEM = """你是一位专业的角色设计师，擅长为小说创作丰富的角色。

请根据小说设定生成角色信息，以JSON格式输出。"""


def _get_ai_service(state: NovelState, **overrides):
    config = state.get("generation_config", {})
    return create_ai_service(
        provider=overrides.pop("provider", config.get("provider", "openai")),
        api_key=overrides.pop("api_key", config.get("api_key", None)),
        base_url=overrides.pop("base_url", config.get("base_url", None)),
        model=overrides.pop("model", config.get("model", settings.default_ai_model)),
        temperature=overrides.pop("temperature", config.get("temperature", 0.8)),
        max_tokens=overrides.pop("max_tokens", config.get("max_tokens", 16000)),
        **overrides,
    )


def _get_world_context(state: NovelState) -> str:
    world = state.get("world_setting", {})
    parts = []
    for key, label in [("time_period", "时代"), ("geography", "地理"), ("power_system", "力量体系"),
                        ("factions", "势力"), ("culture", "文化")]:
        val = world.get(key, "")
        if val:
            parts.append(f"{label}: {val[:200]}")
    return "\n".join(parts)


async def generate_protagonist(state: NovelState) -> dict:
    """Generate the protagonist based on story setting."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    description = state.get("description", "")
    world_context = _get_world_context(state)

    prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}
世界观摘要：{world_context}

请生成「主角」的详细设定，以JSON格式输出：
```json
{{
  "id": "char_1",
  "name": "角色名",
  "gender": "男/女",
  "age": 18,
  "role_type": "protagonist",
  "appearance": "外貌描述（80-150字）",
  "personality": "性格描述（80-150字）",
  "background": "背景故事（150-300字）",
  "goals": "人生目标/驱动力",
  "secrets": "隐藏的秘密（可为空）",
  "mental_state": "当前心理状态",
  "power_level": "当前战力/等级",
  "location": "当前位置",
  "motto": "口头禅/信条",
  "color": "#FF6B6B"
}}
```

要求：角色需适配{genre}类型，性格复杂立体，避免脸谱化。只输出JSON。"""

    try:
        result = await ai.generate_json(CHAR_GEN_SYSTEM, prompt)
        result.setdefault("id", "char_1")
        result.setdefault("role_type", "protagonist")
        characters = state.get("characters", [])
        characters = [c for c in characters if c.get("role_type") != "protagonist"]
        characters.append(result)
        return {"characters": characters, "current_phase": "protagonist_generated"}
    except Exception as e:
        logger.error("generate_protagonist failed: %s", e)
        return {"current_phase": "protagonist_generated", "error": str(e)}


async def generate_supporting(state: NovelState) -> dict:
    """Generate supporting characters."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    world_context = _get_world_context(state)
    existing_chars = state.get("characters", [])
    existing_names = ", ".join(c.get("name", "") for c in existing_chars)
    existing_count = len(existing_chars)

    prompt = f"""小说标题：{title}
类型：{genre}
世界观摘要：{world_context}
已有角色：{existing_names}

请生成3-5个配角，以JSON数组格式输出：
```json
[
  {{
    "id": "char_{existing_count + 1}",
    "name": "角色名",
    "gender": "男/女",
    "age": 20,
    "role_type": "supporting",
    "appearance": "外貌描述（50-100字）",
    "personality": "性格描述（50-100字）",
    "background": "背景故事（100-200字）",
    "goals": "个人目标",
    "relationship_to_protagonist": "与主角的关系",
    "mental_state": "心理状态",
    "power_level": "战力/等级",
    "color": "#4ECDC4"
  }}
]
```

要求：配角需与主角形成互补或对比，各具特色。只输出JSON数组。"""

    try:
        result = await ai.generate_json(CHAR_GEN_SYSTEM, prompt, max_retries=3)
        if isinstance(result, dict):
            result = [result]
        characters = state.get("characters", [])
        for i, char in enumerate(result):
            char.setdefault("id", f"char_{existing_count + i + 1}")
            char.setdefault("role_type", "supporting")
        characters.extend(result)
        return {"characters": characters, "current_phase": "supporting_generated"}
    except Exception as e:
        logger.error("generate_supporting failed: %s", e)
        return {"current_phase": "supporting_generated", "error": str(e)}


async def generate_antagonist(state: NovelState) -> dict:
    """Generate the antagonist."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    world_context = _get_world_context(state)
    existing_chars = state.get("characters", [])
    protagonist_name = ""
    for c in existing_chars:
        if c.get("role_type") == "protagonist":
            protagonist_name = c.get("name", "主角")
            break

    prompt = f"""小说标题：{title}
类型：{genre}
世界观摘要：{world_context}
主角：{protagonist_name}

请生成1-2个「反派/对手」角色设定，以JSON数组格式输出：
```json
[
  {{
    "id": "char_ant_1",
    "name": "反派名",
    "gender": "男/女",
    "age": 30,
    "role_type": "antagonist",
    "appearance": "外貌描述（80-120字）",
    "personality": "性格描述（80-120字）",
    "background": "背景故事（150-300字）",
    "goals": "邪恶目标/动机",
    "secrets": "隐藏的秘密",
    "relationship_to_protagonist": "与主角的冲突关系",
    "mental_state": "心理状态",
    "power_level": "战力/等级",
    "color": "#FF4757"
  }}
]
```

要求：反派需有深度，不是纯粹的恶，要有合理的动机和复杂的性格。只输出JSON数组。"""

    try:
        result = await ai.generate_json(CHAR_GEN_SYSTEM, prompt)
        if isinstance(result, dict):
            result = [result]
        characters = state.get("characters", [])
        for char in result:
            char.setdefault("role_type", "antagonist")
        characters.extend(result)
        return {"characters": characters, "current_phase": "antagonist_generated"}
    except Exception as e:
        logger.error("generate_antagonist failed: %s", e)
        return {"current_phase": "antagonist_generated", "error": str(e)}


async def assign_career(state: NovelState) -> dict:
    """Assign careers and power levels to characters."""
    ai = _get_ai_service(state)
    characters = state.get("characters", [])
    careers = state.get("careers", [])

    if not characters:
        return {"current_phase": "careers_assigned"}

    career_names = ", ".join(c.get("name", "") for c in careers) if careers else "暂无设定职业体系"
    char_list = "\n".join(f"- {c.get('name', '')} (角色: {c.get('role_type', '')}, 当前战力: {c.get('power_level', '未知')})"
                          for c in characters[:10])

    prompt = f"""现有职业体系：{career_names}
角色列表：
{char_list}

请为每个角色分配合适的职业和在职业体系中的等级，以JSON数组格式输出：
```json
[
  {{"character_name": "角色名", "career_name": "职业名", "level": "当前等级", "level_index": 1}}
]
```
只输出JSON数组。"""

    try:
        result = await ai.generate_json(CHAR_GEN_SYSTEM, prompt)
        if isinstance(result, dict):
            result = [result]
        # Update characters with career info
        for assignment in result:
            for char in characters:
                if char.get("name") == assignment.get("character_name"):
                    char["career_id"] = assignment.get("career_name", "")
                    char["career_level"] = assignment.get("level", "")
                    char["career_level_index"] = assignment.get("level_index", 1)
        return {"characters": characters, "current_phase": "careers_assigned"}
    except Exception as e:
        logger.error("assign_career failed: %s", e)
        return {"current_phase": "careers_assigned", "error": str(e)}


async def assign_organization(state: NovelState) -> dict:
    """Assign characters to organizations/factions."""
    ai = _get_ai_service(state)
    characters = state.get("characters", [])
    organizations = state.get("organizations", [])

    if not characters:
        return {"current_phase": "organizations_assigned"}

    org_names = ", ".join(o.get("name", "") for o in organizations) if organizations else "暂无设定组织"
    char_list = "\n".join(f"- {c.get('name', '')} (角色: {c.get('role_type', '')})" for c in characters[:10])

    prompt = f"""现有组织/势力：{org_names}
角色列表：
{char_list}

请为每个角色分配其所属组织，以JSON数组格式输出：
```json
[
  {{"character_name": "角色名", "organization_name": "组织名", "position": "职位/地位"}}
]
```
只输出JSON数组。"""

    try:
        result = await ai.generate_json(CHAR_GEN_SYSTEM, prompt)
        if isinstance(result, dict):
            result = [result]
        for assignment in result:
            for char in characters:
                if char.get("name") == assignment.get("character_name"):
                    char["org_id"] = assignment.get("organization_name", "")
                    char["org_position"] = assignment.get("position", "")
        return {"characters": characters, "current_phase": "organizations_assigned"}
    except Exception as e:
        logger.error("assign_organization failed: %s", e)
        return {"current_phase": "organizations_assigned", "error": str(e)}


async def check_ooc(state: NovelState) -> dict:
    """Check all characters for out-of-character consistency."""
    ai = _get_ai_service(state)
    characters = state.get("characters", [])
    world = _get_world_context(state)

    if not characters:
        return {"current_phase": "ooc_checked"}

    char_descriptions = "\n\n".join(
        f"角色: {c.get('name', '')}\n"
        f"性别: {c.get('gender', '')}\n"
        f"年龄: {c.get('age', '')}\n"
        f"性格: {c.get('personality', '')}\n"
        f"背景: {c.get('background', '')[:200]}\n"
        f"职业: {c.get('career_id', '无')}\n"
        f"战力: {c.get('power_level', '未知')}"
        for c in characters[:8]
    )

    prompt = f"""世界观摘要：{world}

角色列表：
{char_descriptions}

请检查这些角色设定是否存在以下问题：
1. 角色之间是否存在过于雷同的设定
2. 角色能力是否与世界观设定冲突
3. 角色背景是否与世界观时间线矛盾
4. 角色性格与职业/地位是否匹配

以JSON格式输出：
```json
{{
  "has_issues": true/false,
  "issues": ["问题描述1", "问题描述2"],
  "suggestions": ["改进建议1", "改进建议2"]
}}
```
只输出JSON。"""

    try:
        result = await ai.generate_json("你是一位严格的角色一致性审查员。只输出JSON。", prompt)
        has_issues = result.get("has_issues", False)
        issues = result.get("issues", [])
        if issues:
            logger.warning("OOC check found %d issues: %s", len(issues), issues)
        return {"current_phase": "ooc_checked",
                "human_feedback": "; ".join(issues) if issues else None}
    except Exception as e:
        logger.error("check_ooc failed: %s", e)
        return {"current_phase": "ooc_checked", "error": str(e)}


def route_after_check(state: NovelState) -> Literal["done", "fix_issues"]:
    feedback = state.get("human_feedback", "")
    if feedback and state.get("current_phase") == "ooc_checked":
        return "fix_issues"
    return "done"


def create_char_create_subgraph():
    """Create the Character Creation subgraph.

    Generates characters in order:
        protagonist → supporting → antagonist → assign_career → assign_organization → check_ooc
    """
    builder = StateGraph(NovelState)

    builder.add_node("generate_protagonist", generate_protagonist)
    builder.add_node("generate_supporting", generate_supporting)
    builder.add_node("generate_antagonist", generate_antagonist)
    builder.add_node("assign_career", assign_career)
    builder.add_node("assign_organization", assign_organization)
    builder.add_node("check_ooc", check_ooc)

    builder.set_entry_point("generate_protagonist")
    builder.add_edge("generate_protagonist", "generate_supporting")
    builder.add_edge("generate_supporting", "generate_antagonist")
    builder.add_edge("generate_antagonist", "assign_career")
    builder.add_edge("assign_career", "assign_organization")
    builder.add_edge("assign_organization", "check_ooc")
    builder.add_conditional_edges("check_ooc", route_after_check, {"done": END, "fix_issues": "generate_protagonist"})

    return builder.compile()
