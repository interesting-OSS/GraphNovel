"""Chapter API routes — CRUD, AI generation, analysis, rewrite, batch operations.

Powered by LangGraph subgraphs: chapter_write, chapter_analyze, review, batch_gen.
"""
import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from langgraph.checkpoint.memory import MemorySaver

from app.database import get_db
from app.utils.sse_response import SSEResponse, create_sse_response
from app.graphs.state import create_initial_state, NovelState
from app.graphs.main_graph import create_novel_graph
from app.graphs.subgraphs.chapter_write import create_chapter_write_subgraph
from app.graphs.subgraphs.chapter_analyze import create_chapter_analyze_subgraph
from app.services.ai_service import create_ai_service
from app.services.task_service import task_service
from app.config import settings
from app.logger import get_logger
from app.models.chapter import Chapter
from app.models.project import Project
from sqlalchemy import select

router = APIRouter(prefix="/chapters", tags=["chapters"])
logger = get_logger(__name__)


def _parse_state(data: dict) -> dict:
    """Extract NovelState-like dict from the incoming request."""
    config = data.get("generation_config", {})
    return {
        "project_id": data.get("project_id", ""),
        "title": data.get("title", ""),
        "genre": data.get("genre", "玄幻"),
        "description": data.get("description", ""),
        "narrative_perspective": data.get("narrative_perspective", "第三人称"),
        "world_setting": data.get("world_setting", {}),
        "outlines": data.get("outlines", []),
        "characters": data.get("characters", []),
        "chapters": data.get("chapters", []),
        "current_chapter_index": data.get("current_chapter_index", 0),
        "chapter_analyses": data.get("chapter_analyses", []),
        "foreshadows": data.get("foreshadows", []),
        "plot_memory": data.get("plot_memory", []),
        "generation_history": data.get("generation_history", []),
        "writing_style_id": data.get("writing_style_id"),
        "active_skill": data.get("active_skill"),
        "human_feedback": data.get("human_feedback"),
        "generation_config": {
            "provider": config.get("provider", "openai"),
            "model": config.get("model", settings.default_ai_model),
            "temperature": config.get("temperature", 0.7),
            "max_tokens": config.get("max_tokens", 32000),
            "api_key": config.get("api_key"),
            "base_url": config.get("base_url"),
        },
    }


# =========== CRUD ===========


@router.get("/project/{project_id}")
async def list_chapters(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all chapters for a project."""
    result = await db.execute(
        select(Chapter).where(Chapter.project_id == project_id).order_by(Chapter.chapter_index)
    )
    chapters = result.scalars().all()
    return {
        "items": [{"id": c.id, "index": c.chapter_index, "title": c.title,
                    "word_count": c.word_count, "status": c.status} for c in chapters],
        "total": len(chapters),
    }


@router.get("/{chapter_id}")
async def get_chapter(chapter_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single chapter by ID."""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return {
        "id": chapter.id, "index": chapter.chapter_index, "title": chapter.title,
        "content": chapter.content, "word_count": chapter.word_count,
        "status": chapter.status, "project_id": chapter.project_id,
    }


@router.post("")
async def create_chapter(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new chapter."""
    chapter = Chapter(
        project_id=data.get("project_id", ""),
        chapter_index=data.get("chapter_index", data.get("index", 0)),
        title=data.get("title", "新章节"),
        content=data.get("content", ""),
        word_count=data.get("word_count", 0),
        status=data.get("status", "draft"),
    )
    db.add(chapter)
    await db.commit()
    await db.refresh(chapter)
    return {"id": chapter.id, "created": True}


@router.put("/{chapter_id}")
async def update_chapter(chapter_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update an existing chapter."""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    for key in ("title", "content", "word_count", "status"):
        if key in data:
            setattr(chapter, key, data[key])
    await db.commit()
    return {"id": chapter_id, "updated": True}


@router.delete("/{chapter_id}")
async def delete_chapter(chapter_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a chapter."""
    result = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")
    await db.delete(chapter)
    await db.commit()
    return {"deleted": True}


# =========== AI Generation (SSE Streaming via LangGraph) ===========


@router.post("/{chapter_id}/generate-stream")
async def generate_chapter_stream(chapter_id: str, data: dict):
    """Generate chapter content via LangGraph ChapterWrite subgraph with SSE streaming."""
    async def event_generator():
        try:
            state_dict = _parse_state(data)
            state = create_initial_state(
                project_id=state_dict.get("project_id", ""),
                title=state_dict.get("title", ""),
                genre=state_dict.get("genre", "玄幻"),
            )
            for key, value in state_dict.items():
                if key in state:
                    state[key] = value

            yield SSEResponse.progress("准备写作上下文...", 5.0, "preparing")

            # Run the chapter write subgraph
            subgraph = create_chapter_write_subgraph()
            config_ctx = {"configurable": {"thread_id": f"chapter_gen_{chapter_id}"}}

            # Stream through subgraph nodes
            async for event in subgraph.astream(state, config_ctx):
                for node_name, node_output in event.items():
                    if node_name == "build_context":
                        yield SSEResponse.progress("正在构建写作上下文...", 15.0, "preparing")
                    elif node_name == "generate_draft":
                        yield SSEResponse.progress("正在生成章节内容...", 30.0, "generating")
                        # If the node output contains actual chapter content, stream it
                        chapters = node_output.get("chapters", [])
                        for ch in chapters:
                            content = ch.get("content", "")
                            if content:
                                # Stream content in chunks for real-time display
                                chunk_size = 100
                                for i in range(0, len(content), chunk_size):
                                    yield SSEResponse.chunk(content[i:i + chunk_size])
                                    await asyncio.sleep(0.01)
                    elif node_name == "save_generation_history":
                        yield SSEResponse.progress("保存生成版本...", 95.0, "saving")

            # Get final state
            final_state = await subgraph.aget_state(config_ctx)
            final_values = final_state.values if final_state else {}
            chapters = final_values.get("chapters", [])

            yield SSEResponse.progress("生成完成", 100.0, "complete")
            yield SSEResponse.result({"chapters": chapters})
            yield SSEResponse.done("章节生成完成")

        except Exception as e:
            logger.exception("Chapter generation failed for %s", chapter_id)
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{chapter_id}/analyze")
async def analyze_chapter(chapter_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Run chapter analysis via LangGraph ChapterAnalyze subgraph."""
    try:
        state_dict = _parse_state(data)
        state = create_initial_state(project_id=state_dict.get("project_id", ""))
        for key, value in state_dict.items():
            if key in state:
                state[key] = value

        subgraph = create_chapter_analyze_subgraph()
        config_ctx = {"configurable": {"thread_id": f"chapter_analyze_{chapter_id}"}}

        result = await subgraph.ainvoke(state, config_ctx)
        chapter_analyses = result.get("chapter_analyses", [])
        idx = result.get("current_chapter_index", 0)

        # Find the relevant analysis
        analysis = {}
        for a in chapter_analyses:
            if a.get("chapter_index") == idx:
                analysis = a
                break

        return {"analysis": analysis, "status": "completed"}
    except Exception as e:
        logger.exception("Chapter analysis failed for %s", chapter_id)
        return {"status": "failed", "error": str(e)}


@router.post("/{chapter_id}/polish")
async def polish_chapter(chapter_id: str, data: dict):
    """Polish chapter prose via SSE streaming."""
    async def event_generator():
        try:
            ai = create_ai_service(
                provider=data.get("provider", "openai"),
                api_key=data.get("api_key"),
                model=data.get("model", settings.default_ai_model),
                temperature=0.5,
                max_tokens=32000,
            )
            content = data.get("content", "")
            if not content:
                yield SSEResponse.error("无章节内容")
                return

            yield SSEResponse.progress("正在润色...", 20.0, "polishing")

            prompt = f"""你是一位资深小说编辑。请润色以下章节，优化语言流畅度、用词精准度、节奏把控。
保持原文风格和情节不变，只做文笔层面的优化。

原文：
{content[:15000]}

请输出润色后的完整章节："""

            full_response = ""
            async for chunk in ai.generate_stream("你是一位资深小说编辑。", prompt):
                full_response += chunk
                yield SSEResponse.chunk(chunk)

            yield SSEResponse.result({"polished_content": full_response})
            yield SSEResponse.done("润色完成")

        except Exception as e:
            logger.exception("Polish failed for %s", chapter_id)
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{chapter_id}/rewrite")
async def rewrite_chapter(chapter_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Rewrite chapter based on user feedback."""
    try:
        ai = create_ai_service(
            provider=data.get("provider", "openai"),
            api_key=data.get("api_key"),
            model=data.get("model", settings.default_ai_model),
            temperature=0.7,
            max_tokens=32000,
        )
        content = data.get("content", "")
        feedback = data.get("feedback", "请改善")

        prompt = f"""你是一位资深小说编辑。请根据反馈重写以下章节：

用户反馈：{feedback}

原文：
{content[:15000]}

请输出重写后的完整章节："""

        result = await ai.generate("你是一位专业的小说编辑。", prompt)
        return {"rewritten_content": result.strip(), "status": "rewritten"}
    except Exception as e:
        logger.exception("Rewrite failed for %s", chapter_id)
        return {"status": "failed", "error": str(e)}


@router.post("/{chapter_id}/partial-regenerate-stream")
async def partial_regenerate_stream(chapter_id: str, data: dict):
    """Partial regenerate (rewrite selected text) via SSE streaming."""
    async def event_generator():
        try:
            ai = create_ai_service(
                provider=data.get("provider", "openai"),
                api_key=data.get("api_key"),
                model=data.get("model", settings.default_ai_model),
                temperature=0.7,
                max_tokens=8000,
            )
            selected_text = data.get("selected_text", "")
            strategy = data.get("strategy", "similar")
            custom_instruction = data.get("custom_instruction", "")

            if not selected_text:
                yield SSEResponse.error("未选中文本")
                return

            strategy_prompts = {
                "similar": "请保持原文风格重写以下段落。",
                "expand": "请在保持风格的基础上扩展细节和描写。",
                "condense": "请精简以下内容，去除冗余但保留核心信息。",
                "custom": f"请根据以下指令重写：{custom_instruction}",
            }
            instruction = strategy_prompts.get(strategy, strategy_prompts["similar"])

            yield SSEResponse.progress("正在重写选中段落...", 30.0, "rewriting")

            prompt = f"""你是一位小说编辑。
{instruction}

原文段落：
{selected_text[:3000]}

请输出重写后的内容："""

            full_response = ""
            async for chunk in ai.generate_stream("你是一位资深小说编辑。", prompt):
                full_response += chunk
                yield SSEResponse.chunk(chunk)

            yield SSEResponse.result({"rewritten": full_response})
            yield SSEResponse.done("部分重写完成")

        except Exception as e:
            logger.exception("Partial regenerate failed for %s", chapter_id)
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# =========== Multi-Agent Review ===========


@router.post("/{chapter_id}/review")
async def run_multi_agent_review(chapter_id: str, db: AsyncSession = Depends(get_db)):
    """Run 4 parallel review agents on a chapter and return the combined report.

    Triggers the ReviewSubGraph: reader_review + logic_check + prose_check + pacing_check.
    """
    from app.models.chapter import Chapter
    from app.graphs.subgraphs.review import create_review_subgraph
    result_ch = await db.execute(select(Chapter).where(Chapter.id == chapter_id))
    chapter = result_ch.scalar_one_or_none()
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    subgraph = create_review_subgraph()
    state = {
        "project_id": chapter.project_id,
        "current_chapter_index": chapter.chapter_index,
        "chapters": [{
            "id": chapter.id, "index": chapter.chapter_index,
            "title": chapter.title or "", "content": chapter.content or "",
        }],
        "current_phase": "start",
    }
    result = await subgraph.ainvoke(state)
    return {
        "reader_review": result.get("_reader_review", {}),
        "logic_check": result.get("_logic_check", {}),
        "prose_check": result.get("_prose_check", {}),
        "pacing_check": result.get("_pacing_check", {}),
        "aggregate": result.get("_aggregate_report", {}),
    }


# =========== Batch Operations ===========


@router.post("/project/{project_id}/batch-generate")
async def batch_generate(project_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Create a batch generation background task."""
    task_id = await task_service.create(
        project_id=project_id,
        task_type="batch_generate",
        config={
            "start_chapter": data.get("start_chapter", 1),
            "end_chapter": data.get("end_chapter", 5),
            "generation_config": data.get("generation_config", {}),
        },
    )
    return {"task_id": task_id, "message": "批量生成任务已创建"}


@router.get("/project/{project_id}/batch-generate/{batch_id}/status")
async def batch_generate_status(project_id: str, batch_id: str):
    """Get batch generation task status."""
    task = await task_service.get(batch_id)
    if not task:
        return {"status": "unknown", "message": "Task not found"}
    return {
        "status": task["status"],
        "progress": task["progress"],
        "error_message": task.get("error_message"),
    }


# =========== Generation History ===========


@router.get("/{chapter_id}/generation-history")
async def get_generation_history(chapter_id: str, db: AsyncSession = Depends(get_db)):
    """Get generation version history for a chapter."""
    from app.models.generation import GenerationHistory
    result = await db.execute(
        select(GenerationHistory)
        .where(GenerationHistory.chapter_id == chapter_id)
        .order_by(GenerationHistory.version.desc())
    )
    entries = result.scalars().all()
    return {
        "versions": [{"id": e.id, "version": e.version, "created_at": str(e.created_at),
                       "word_count": len(e.content) if e.content else 0} for e in entries],
    }


@router.get("/{chapter_id}/diff")
async def get_diff(chapter_id: str, version_a: int = Query(...), version_b: int = Query(...),
                   db: AsyncSession = Depends(get_db)):
    """Get diff between two chapter versions."""
    from app.models.generation import GenerationHistory
    result_a = await db.execute(
        select(GenerationHistory).where(
            GenerationHistory.chapter_id == chapter_id,
            GenerationHistory.version == version_a,
        )
    )
    result_b = await db.execute(
        select(GenerationHistory).where(
            GenerationHistory.chapter_id == chapter_id,
            GenerationHistory.version == version_b,
        )
    )
    entry_a = result_a.scalar_one_or_none()
    entry_b = result_b.scalar_one_or_none()

    if not entry_a or not entry_b:
        return {"diff": "", "message": "版本不存在"}

    # Simple diff: return both versions for frontend diff viewer
    return {
        "version_a": version_a,
        "version_b": version_b,
        "content_a": entry_a.content or "",
        "content_b": entry_b.content or "",
    }
