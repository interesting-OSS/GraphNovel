"""Project Creation Wizard — SSE streaming API driven by LangGraph graph invocation.

Each endpoint executes a LangGraph subgraph and streams progress events via SSE.
"""
import json
import asyncio
from typing import AsyncGenerator
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.memory import MemorySaver

from app.database import get_db
from app.utils.sse_response import SSEResponse
from app.graphs.state import create_initial_state
from app.graphs.main_graph import create_novel_graph
from app.services.ai_service import create_ai_service
from app.config import settings
from app.logger import get_logger

router = APIRouter(prefix="/wizard-stream", tags=["wizard_stream"])
logger = get_logger(__name__)


def _get_ai_from_request(data: dict) -> "AIService":
    return create_ai_service(
        provider=data.get("provider", "openai"),
        api_key=data.get("api_key"),
        base_url=data.get("base_url"),
        model=data.get("model", settings.default_ai_model),
        temperature=data.get("temperature", 0.7),
        max_tokens=data.get("max_tokens", 32000),
    )


@router.post("/world-building")
async def generate_world_building(request: Request, db: AsyncSession = Depends(get_db)):
    """Generate world building via LangGraph WorldBuild subgraph with SSE streaming."""
    async def event_generator():
        try:
            data = await request.json()
            project_id = data.get("project_id", "")
            genre = data.get("genre", "玄幻")
            title = data.get("title", "")
            description = data.get("description", "")

            # Build initial state
            state = create_initial_state(
                project_id=project_id,
                title=title,
                genre=genre,
                generation_config={
                    "provider": data.get("provider", "openai"),
                    "model": data.get("model", settings.default_ai_model),
                    "temperature": 0.7,
                    "max_tokens": 32000,
                },
            )
            if description:
                state["description"] = description

            # Create a dedicated graph instance with memory checkpointer
            graph = create_novel_graph(checkpointer=MemorySaver())
            config_ctx = {"configurable": {"thread_id": f"wizard_world_{project_id}"}}

            yield SSEResponse.progress("初始化世界观构建...", 5.0, "init")

            # Stream graph events
            dimensions = [
                ("generate_time_period", "时代背景", 15.0),
                ("generate_geography", "地理版图", 30.0),
                ("generate_power_system", "力量体系", 50.0),
                ("generate_factions", "势力格局", 70.0),
                ("generate_culture", "文化风俗", 90.0),
            ]

            # Run the world_build subgraph step by step for detailed progress
            async for event in graph.astream(state, config_ctx, subgraphs=True):
                for node_name, node_output in event.items():
                    for dim_name, dim_label, progress in dimensions:
                        if dim_name in node_name:
                            yield SSEResponse.progress(
                                f"正在生成{dim_label}...", progress, "generating")
                            break

            # Get final state
            final_state = await graph.aget_state(config_ctx)
            values = final_state.values if final_state else {}
            world_setting = values.get("world_setting", {})
            if not world_setting:
                # Fallback: run directly
                ai = _get_ai_from_request(data)
                world_setting = await _generate_world_direct(ai, title, genre, description)

            yield SSEResponse.result({"world_setting": world_setting})
            yield SSEResponse.done("世界观构建完成")

        except Exception as e:
            logger.exception("World building failed")
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _generate_world_direct(ai, title: str, genre: str, description: str) -> dict:
    """Fallback: generate world building directly without graph."""
    world = {}
    dimensions = [
        ("time_period", "时代背景"),
        ("geography", "地理版图"),
        ("power_system", "力量体系"),
        ("factions", "势力格局"),
        ("culture", "文化风俗"),
    ]
    for key, label in dimensions:
        prompt = f"小说标题：{title}\n类型：{genre}\n简介：{description}\n\n请生成「{label}」设定（300-500字）。只输出纯文本。"
        result = await ai.generate("你是一位世界观架构师。", prompt)
        world[key] = result.strip()
    return world


@router.post("/characters")
async def generate_characters(request: Request, db: AsyncSession = Depends(get_db)):
    """Generate characters via LangGraph CharCreate subgraph with SSE streaming."""
    async def event_generator():
        try:
            data = await request.json()
            project_id = data.get("project_id", "")
            genre = data.get("genre", "玄幻")
            title = data.get("title", "")
            description = data.get("description", "")
            world_setting = data.get("world_setting", {})

            state = create_initial_state(
                project_id=project_id,
                title=title,
                genre=genre,
                generation_config={
                    "provider": data.get("provider", "openai"),
                    "model": data.get("model", settings.default_ai_model),
                    "temperature": 0.8,
                    "max_tokens": 16000,
                },
            )
            state["description"] = description
            state["world_setting"] = world_setting

            yield SSEResponse.progress("开始角色创建...", 10.0, "init")

            # Generate characters directly with AI service for fine-grained progress
            ai = _get_ai_from_request(data)

            yield SSEResponse.progress("正在生成主角...", 25.0, "generating")
            protagonist = await _generate_character(ai, "protagonist", title, genre, description, world_setting)

            yield SSEResponse.progress("正在生成配角...", 55.0, "generating")
            supporting = await _generate_characters_batch(ai, "supporting", title, genre, description, world_setting, [protagonist])

            yield SSEResponse.progress("正在生成反派...", 80.0, "generating")
            antagonist = await _generate_characters_batch(ai, "antagonist", title, genre, description, world_setting, [protagonist] + supporting)

            characters = [protagonist] + supporting + antagonist

            yield SSEResponse.result({"characters": characters})
            yield SSEResponse.done("角色生成完成")

        except Exception as e:
            logger.exception("Character generation failed")
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _generate_character(ai, role_type: str, title: str, genre: str, description: str, world_setting: dict) -> dict:
    role_labels = {"protagonist": "主角", "supporting": "配角", "antagonist": "反派"}
    label = role_labels.get(role_type, "角色")

    prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}
世界观摘要：{json.dumps({k: world_setting.get(k, '')[:100] for k in ['time_period', 'power_system', 'factions']}, ensure_ascii=False)}

请生成「{label}」的详细设定，以JSON格式输出：
```json
{{
  "id": "char_{role_type}_1",
  "name": "角色名",
  "gender": "男/女",
  "age": 20,
  "role_type": "{role_type}",
  "appearance": "外貌描述（80-150字）",
  "personality": "性格描述（80-150字）",
  "background": "背景故事（100-200字）",
  "goals": "人生目标",
  "secrets": "隐藏的秘密",
  "mental_state": "当前心理状态",
  "power_level": "战力/等级",
  "color": "#4ECDC4"
}}
```
只输出JSON。"""

    try:
        result = await ai.generate_json("你是一位专业的角色设计师。只输出JSON。", prompt)
        result.setdefault("id", f"char_{role_type}_1")
        result.setdefault("role_type", role_type)
        return result
    except Exception:
        return {"id": f"char_{role_type}_1", "name": f"未命名{label}", "role_type": role_type}


async def _generate_characters_batch(ai, role_type: str, title: str, genre: str, description: str,
                                      world_setting: dict, existing: list) -> list:
    role_labels = {"supporting": "配角", "antagonist": "反派"}
    label = role_labels.get(role_type, "角色")
    existing_names = ", ".join(c.get("name", "") for c in existing)

    prompt = f"""小说标题：{title}
类型：{genre}
已有角色：{existing_names}

请生成2-3个{label}，以JSON数组格式输出。每个角色包含：name, gender, age, role_type ("{role_type}"), appearance, personality, background, goals, secrets, mental_state, power_level, color。只输出JSON数组。"""

    try:
        result = await ai.generate_json("你是一位角色设计师。只输出JSON数组。", prompt)
        if isinstance(result, dict):
            result = [result]
        for i, char in enumerate(result):
            char.setdefault("id", f"char_{role_type}_{i + 2}")
            char.setdefault("role_type", role_type)
        return result
    except Exception:
        return []


@router.post("/careers")
async def generate_careers(request: Request, db: AsyncSession = Depends(get_db)):
    """Generate career systems via SSE."""
    async def event_generator():
        try:
            data = await request.json()
            ai = _get_ai_from_request(data)
            genre = data.get("genre", "玄幻")
            world_setting = data.get("world_setting", {})

            yield SSEResponse.progress("正在生成职业体系...", 30.0, "generating")

            prompt = f"""小说类型：{genre}
力量体系：{world_setting.get('power_system', '未设定')}

请设计1-3个职业体系，每个包含5-10个等级。以JSON数组格式输出：
```json
[{{"id": "career_1", "name": "职业名", "description": "描述", "levels": [{{"name": "等级名", "index": 1, "description": "描述", "abilities": ["能力"]}}]}}]
```
只输出JSON数组。"""

            result = await ai.generate_json("你是一位职业体系设计师。只输出JSON数组。", prompt)
            if isinstance(result, dict):
                result = [result]

            yield SSEResponse.result({"careers": result})
            yield SSEResponse.done("职业体系生成完成")
        except Exception as e:
            logger.exception("Career generation failed")
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/outline")
async def generate_outline(request: Request, db: AsyncSession = Depends(get_db)):
    """Generate story outline via SSE."""
    async def event_generator():
        try:
            data = await request.json()
            ai = _get_ai_from_request(data)
            title = data.get("title", "")
            genre = data.get("genre", "玄幻")
            description = data.get("description", "")
            target_words = data.get("target_words", 100000)
            outline_mode = data.get("outline_mode", "one-to-one")
            world_setting = data.get("world_setting", {})

            yield SSEResponse.progress("正在规划大纲结构...", 20.0, "generating")

            yield SSEResponse.progress("正在生成章节要点...", 50.0, "generating")

            prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}
目标字数：{target_words:,}字
大纲模式：{outline_mode}
世界观：{json.dumps({k: world_setting.get(k, '')[:100] for k in ['time_period', 'power_system', 'factions']}, ensure_ascii=False)}

请规划小说大纲，以JSON格式输出：
```json
{{
  "volumes": 3,
  "outlines": [
    {{"volume": 1, "chapter_num": 1, "title": "章节标题", "summary": "摘要（50-150字）", "key_points": "关键要点", "target_words": 3000, "mode": "{outline_mode}", "expansion_strategy": "balanced"}}
  ]
}}
```
要求：根据目标字数合理分配章节数（每章2000-4000字），遵循开端→发展→转折→高潮→结局的结构。只输出JSON。"""

            result = await ai.generate_json("你是一位小说结构规划师。只输出JSON。", prompt)
            outlines = result.get("outlines", [])

            yield SSEResponse.result({"outlines": outlines, "volumes": result.get("volumes", 1)})
            yield SSEResponse.done("大纲生成完成")

        except Exception as e:
            logger.exception("Outline generation failed")
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
