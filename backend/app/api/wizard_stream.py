"""Project Creation Wizard — SSE streaming API driven by LangGraph graph invocation.

Each endpoint executes a LangGraph subgraph and streams progress events via SSE.

IMPORTANT: request.json() MUST be called OUTSIDE the event generator, because
FastAPI starts streaming the response (200 + headers) before the generator runs,
and the request body is no longer available once streaming begins.
"""
import json
import asyncio
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.sse_response import SSEResponse
from app.graphs.state import create_initial_state, NovelState
from app.graphs.subgraphs.world_build import create_world_build_subgraph
from app.graphs.subgraphs.char_create import create_char_create_subgraph
from app.services.ai_service import create_ai_service, AIService
from app.config import settings
from app.graphs.utils import get_gen_config
from app.logger import get_logger
from app.services.generation_tracker import tracker

router = APIRouter(prefix="/wizard-stream", tags=["wizard_stream"])
logger = get_logger(__name__)


def _get_ai_from_request(data: dict) -> AIService:
    cfg = get_gen_config(data)
    return create_ai_service(
        provider=cfg["provider"], api_key=cfg["api_key"],
        base_url=cfg["base_url"], model=cfg["model"],
        temperature=cfg["temperature"], max_tokens=cfg["max_tokens"],
    )


# ── World Building ──────────────────────────────────────────────────────────

@router.post("/world-building")
async def generate_world_building(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()  # MUST read body before generator

    async def event_generator():
        project_id = ""
        try:
            project_id = data.get("project_id", "")
            genre = data.get("genre", "玄幻")
            title = data.get("title", "")
            description = data.get("description", "")

            state = create_initial_state(
                project_id=project_id, title=title, genre=genre,
                generation_config=get_gen_config(data),
            )
            if description:
                state["description"] = description

            tracker.start(project_id or "unknown", "world_build", "世界观构建")
            subgraph = create_world_build_subgraph()
            config_ctx = {"configurable": {"thread_id": f"wizard_world_{project_id}"}}

            tracker.update(project_id or "unknown", phase="init", label="初始化...", progress=5.0)
            yield SSEResponse.progress("初始化世界观构建...", 5.0, "init")

            dimensions = [
                ("generate_time_period", "时代背景", 15.0),
                ("generate_geography", "地理版图", 30.0),
                ("generate_power_system", "力量体系", 50.0),
                ("generate_factions", "势力格局", 70.0),
                ("generate_culture", "文化风俗", 90.0),
            ]

            world_setting = {}
            async for event in subgraph.astream(state, config_ctx):
                for node_name, node_output in event.items():
                    matched = False
                    for dim_name, dim_label, progress in dimensions:
                        if dim_name in node_name:
                            tracker.update(project_id or "unknown", phase="generating",
                                           label=f"正在生成{dim_label}", progress=progress)
                            yield SSEResponse.progress(f"正在生成{dim_label}...", progress, "generating")
                            matched = True; break
                    if not matched:
                        if node_name == "check_consistency":
                            yield SSEResponse.progress("正在检查世界观一致性...", 94.0, "generating")
                        elif node_name == "resolve_conflicts":
                            yield SSEResponse.progress("正在解决设定冲突...", 97.0, "generating")
                    if "world_setting" in node_output:
                        world_setting = node_output["world_setting"]
                    if "error" in node_output and node_output["error"]:
                        raise RuntimeError(str(node_output["error"]))

            # Fallback: if no world_setting from graph, generate directly
            if not world_setting:
                try:
                    ai = _get_ai_from_request(data)
                    world_setting = await _generate_world_direct(ai, title, genre, description)
                except Exception as fallback_err:
                    logger.exception("World building fallback failed")
                    tracker.error(project_id or "unknown", f"AI 调用失败: {fallback_err}")
                    yield SSEResponse.error(f"AI 调用失败，请检查 API Key: {fallback_err}")
                    return

            tracker.finish(project_id or "unknown")
            yield SSEResponse.result({"world_setting": world_setting})
            yield SSEResponse.done("世界观构建完成")

        except Exception as e:
            logger.exception("World building failed")
            err_msg = str(e) or f"AI 服务连接失败（{type(e).__name__}）"
            tracker.error(project_id or "unknown", err_msg)
            yield SSEResponse.error(err_msg)

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


async def _generate_world_direct(ai: AIService, title: str, genre: str, description: str) -> dict:
    world = {}
    for key, label in [("time_period", "时代背景"), ("geography", "地理版图"),
                        ("power_system", "力量体系"), ("factions", "势力格局"),
                        ("culture", "文化风俗")]:
        result = await ai.generate("你是一位世界观架构师。",
            f"小说标题：{title}\n类型：{genre}\n简介：{description}\n\n请生成「{label}」设定（300-500字）。只输出纯文本。")
        world[key] = result.strip()
    return world


# ── Characters ──────────────────────────────────────────────────────────────

@router.post("/characters")
async def generate_characters(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()  # MUST read body before generator

    async def event_generator():
        project_id = ""
        try:
            project_id = data.get("project_id", "")
            genre = data.get("genre", "玄幻")
            title = data.get("title", "")
            description = data.get("description", "")
            world_setting = data.get("world_setting", {})

            tracker.start(project_id or "unknown", "char_create", "角色创建")
            state = create_initial_state(
                project_id=project_id, title=title, genre=genre,
                generation_config=get_gen_config(data, temperature=0.8, max_tokens=16000),
            )
            state["description"] = description
            state["world_setting"] = world_setting

            tracker.update(project_id or "unknown", phase="init", label="开始角色创建...", progress=5.0)
            yield SSEResponse.progress("开始角色创建...", 5.0, "init")

            subgraph = create_char_create_subgraph()
            config_ctx = {"configurable": {"thread_id": f"wizard_char_{project_id}"}}

            node_progress = {
                "generate_protagonist": ("正在生成主角...", 20.0),
                "generate_supporting": ("正在生成配角...", 40.0),
                "generate_antagonist": ("正在生成反派...", 60.0),
                "assign_career": ("正在分配职业...", 70.0),
                "assign_organization": ("正在分配组织...", 78.0),
                "generate_relationships": ("正在生成角色关系...", 86.0),
                "check_ooc": ("正在检查角色一致性...", 94.0),
            }

            characters = []
            relationships = []
            async for event in subgraph.astream(state, config_ctx):
                for node_name, node_output in event.items():
                    for prefix, (label, progress) in node_progress.items():
                        if node_name == prefix or node_name.startswith(prefix):
                            tracker.update(project_id or "unknown", phase="generating",
                                           label=label, progress=progress)
                            yield SSEResponse.progress(label, progress, "generating")
                            break
                    if "characters" in node_output:
                        characters = node_output["characters"]
                    if "character_relationships" in node_output:
                        relationships = node_output["character_relationships"]
                    if "error" in node_output and node_output["error"]:
                        raise RuntimeError(str(node_output["error"]))
            tracker.finish(project_id or "unknown")
            yield SSEResponse.result({"characters": characters, "relationships": relationships})
            yield SSEResponse.done("角色生成完成")

        except Exception as e:
            logger.exception("Character generation failed")
            err_msg = str(e) or f"AI 服务连接失败（{type(e).__name__}）"
            tracker.error(project_id or "unknown", err_msg)
            yield SSEResponse.error(err_msg)

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Careers ─────────────────────────────────────────────────────────────────

@router.post("/careers")
async def generate_careers(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()  # MUST read body before generator

    async def event_generator():
        project_id = ""
        try:
            project_id = data.get("project_id", "")
            genre = data.get("genre", "玄幻")
            world_setting = data.get("world_setting", {})

            tracker.start(project_id or "unknown", "career_manage", "职业体系生成")
            yield SSEResponse.progress("正在准备职业体系生成...", 10.0, "generating")

            tracker.update(project_id or "unknown", phase="generating",
                           label="正在生成职业体系...", progress=30.0)
            yield SSEResponse.progress("正在生成职业体系...", 30.0, "generating")

            from app.graphs.main_graph import career_manage_node
            state = NovelState(
                project_id=project_id, genre=genre, world_setting=world_setting,
                generation_config=get_gen_config(data, max_tokens=8000),
            )

            result = await career_manage_node(state)
            graph_error = result.get("error", "")
            if graph_error:
                tracker.error(project_id or "unknown", f"AI 生成失败: {graph_error}")
                yield SSEResponse.error(f"AI 生成失败: {graph_error}")
                return

            yield SSEResponse.progress("正在保存职业数据...", 90.0, "generating")

            careers = result.get("careers", [])
            tracker.finish(project_id or "unknown")
            yield SSEResponse.result({"careers": careers})
            yield SSEResponse.done("职业体系生成完成")

        except Exception as e:
            logger.exception("Career generation failed")
            err_msg = str(e) or f"AI 服务连接失败（{type(e).__name__}）"
            tracker.error(project_id or "unknown", err_msg)
            yield SSEResponse.error(err_msg)

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Organizations ───────────────────────────────────────────────────────────

@router.post("/organizations")
async def generate_organizations(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()

    async def event_generator():
        project_id = ""
        try:
            project_id = data.get("project_id", "")
            genre = data.get("genre", "玄幻")
            world_setting = data.get("world_setting", {})

            tracker.start(project_id or "unknown", "organization", "组织势力生成")
            yield SSEResponse.progress("正在准备组织势力生成...", 10.0, "generating")

            tracker.update(project_id or "unknown", phase="generating",
                           label="正在生成组织势力...", progress=30.0)
            yield SSEResponse.progress("正在生成组织势力...", 30.0, "generating")

            from app.graphs.main_graph import organization_node
            state = NovelState(
                project_id=project_id, genre=genre, world_setting=world_setting,
                generation_config=get_gen_config(data, max_tokens=8000),
            )

            result = await organization_node(state)
            graph_error = result.get("error", "")
            if graph_error:
                tracker.error(project_id or "unknown", f"AI 生成失败: {graph_error}")
                yield SSEResponse.error(f"AI 生成失败: {graph_error}")
                return

            yield SSEResponse.progress("正在保存组织数据...", 90.0, "generating")

            orgs = result.get("organizations", [])
            tracker.finish(project_id or "unknown")
            yield SSEResponse.result({"organizations": orgs})
            yield SSEResponse.done("组织势力生成完成")

        except Exception as e:
            logger.exception("Organization generation failed")
            err_msg = str(e) or f"AI 服务连接失败（{type(e).__name__}）"
            tracker.error(project_id or "unknown", err_msg)
            yield SSEResponse.error(err_msg)

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


# ── Outline ─────────────────────────────────────────────────────────────────

@router.post("/outline")
async def generate_outline(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()  # MUST read body before generator

    async def event_generator():
        project_id = ""
        try:
            project_id = data.get("project_id", "")
            title = data.get("title", "")
            genre = data.get("genre", "玄幻")
            description = data.get("description", "")
            target_words = data.get("target_words", 100000)
            outline_mode = data.get("outline_mode", "one-to-one")
            world_setting = data.get("world_setting", {})

            tracker.start(project_id or "unknown", "outline_plan", "大纲生成")
            yield SSEResponse.progress("正在准备大纲生成...", 10.0, "generating")
            yield SSEResponse.progress("正在规划大纲结构...", 30.0, "generating")

            from app.graphs.main_graph import outline_plan_node
            state = NovelState(
                project_id=project_id, title=title, genre=genre,
                description=description, target_words=target_words,
                outline_mode=outline_mode, world_setting=world_setting,
                characters=data.get("characters", []),
                generation_config=get_gen_config(data),
            )

            yield SSEResponse.progress("正在生成章节要点...", 50.0, "generating")
            result = await outline_plan_node(state)
            graph_error = result.get("error", "")
            if graph_error:
                tracker.error(project_id or "unknown", f"AI 生成失败: {graph_error}")
                yield SSEResponse.error(f"AI 生成失败: {graph_error}")
                return

            yield SSEResponse.progress("正在保存大纲数据...", 90.0, "generating")

            outlines = result.get("outlines", [])
            tracker.finish(project_id or "unknown")
            yield SSEResponse.result({"outlines": outlines})
            yield SSEResponse.done("大纲生成完成")

        except Exception as e:
            logger.exception("Outline generation failed")
            err_msg = str(e) or f"AI 服务连接失败（{type(e).__name__}）"
            tracker.error(project_id or "unknown", err_msg)
            yield SSEResponse.error(err_msg)

    return StreamingResponse(event_generator(), media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
