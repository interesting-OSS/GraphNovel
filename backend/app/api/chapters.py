"""Chapter API routes — CRUD, AI generation, analysis, rewrite, batch operations.

Powered by LangGraph subgraphs: chapter_write, chapter_analyze, review, batch_gen.
"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.utils.sse_response import SSEResponse
from app.graphs.state import create_initial_state, NovelState
from app.graphs.subgraphs.chapter_write import create_chapter_write_subgraph
from app.graphs.subgraphs.chapter_analyze import create_chapter_analyze_subgraph
from app.services.task_service import task_service
from app.graphs.utils import get_gen_config
from app.services.ai_service import create_ai_service
from app.config import settings
from app.logger import get_logger
from app.models.chapter import Chapter
from sqlalchemy import select

router = APIRouter(prefix="/chapters", tags=["chapters"])
logger = get_logger(__name__)


async def _auto_extract_foreshadows(project_id: str, chapter_index: int, content: str, ai_config: dict) -> int:
    """Auto-detect foreshadows from chapter content and save to DB. Returns count added."""
    if not content or len(content) < 100:
        return 0
    try:
        ai = create_ai_service(
            provider=ai_config.get("provider", "openai"),
            api_key=ai_config.get("api_key"),
            base_url=ai_config.get("base_url"),
            model=ai_config.get("model", settings.default_llm_model),
            temperature=0.3, max_tokens=2000,
        )
        prompt = f"""请从以下章节中识别伏笔和钩子，以JSON格式输出：
```json
{{
  "new_foreshadows": [
    {{"description": "伏笔描述", "category": "人物伏笔/情节伏笔/世界观伏笔/能力伏笔", "importance": 7}}
  ]
}}
```

章节内容：
{content[:6000]}"""
        result = await ai.generate_json("你是一位小说分析师，善于识别伏笔。只输出JSON。", prompt)
        new_items = result.get("new_foreshadows", [])
        if not new_items:
            return 0

        from app.database import async_session_factory
        from app.models.foreshadow import Foreshadow
        async with async_session_factory() as db:
            count = 0
            for fs in new_items:
                foreshadow = Foreshadow(
                    project_id=project_id,
                    description=fs.get("description", ""),
                    category=fs.get("category", "情节伏笔"),
                    importance=float(fs.get("importance", 5)),
                    status="set",
                    set_chapter_id=None,
                    target_chapter_index=chapter_index,
                )
                db.add(foreshadow)
                count += 1
            await db.commit()
        logger.info("Auto-extracted %d foreshadows for ch%d", count, chapter_index)
        return count
    except Exception as e:
        logger.warning("Auto foreshadow extraction skipped: %s", e)
        return 0


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
        "generation_config": get_gen_config(config),
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
        "items": [{"id": c.id, "chapter_index": c.chapter_index, "title": c.title,
                    "content": c.content, "word_count": c.word_count,
                    "status": c.status} for c in chapters],
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
        "id": chapter.id, "chapter_index": chapter.chapter_index, "title": chapter.title,
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
        from app.services.generation_tracker import tracker as gen_tracker
        try:
            state_dict = _parse_state(data)
            project_id = state_dict.get("project_id", chapter_id)
            state = create_initial_state(
                project_id=project_id,
                title=state_dict.get("title", ""),
                genre=state_dict.get("genre", "玄幻"),
            )
            for key, value in state_dict.items():
                if key in state:
                    state[key] = value

            gen_tracker.start(project_id, "chapter_write", "章节写作")
            gen_tracker.update(project_id, phase="preparing", label="准备写作上下文...", progress=5.0)
            yield SSEResponse.progress("准备写作上下文...", 5.0, "preparing")

            # Run the chapter write subgraph
            subgraph = create_chapter_write_subgraph()
            config_ctx = {"configurable": {"thread_id": f"chapter_gen_{chapter_id}"}}

            # Use astream_events to capture LLM streaming tokens in real-time
            chapters = []
            content_buffer = ""
            node_phase = "preparing"
            try:
                async for event in subgraph.astream_events(state, config_ctx, version="v2"):
                    event_type = event.get("event", "")

                    # ── LLM streaming tokens (real-time content) ──
                    if event_type == "on_chat_model_stream":
                        chunk_data = event.get("data", {}).get("chunk")
                        if chunk_data and hasattr(chunk_data, "content") and chunk_data.content:
                            token = chunk_data.content
                            content_buffer += token
                            yield SSEResponse.chunk(token)
                            # Update progress smoothly from 30→80 during streaming
                            if len(content_buffer) % 200 == 0:
                                progress = min(30 + (len(content_buffer) / 200) * 0.5, 79)
                                yield SSEResponse.progress("正在生成章节内容...", progress, "generating")

                    # ── Node lifecycle events ──
                    elif event_type == "on_chain_start":
                        node_name = event.get("name", "")
                        if node_name == "build_context":
                            node_phase = "preparing"
                            gen_tracker.update(project_id, phase="preparing", label="正在构建写作上下文...", progress=15.0)
                            yield SSEResponse.progress("正在构建写作上下文...", 15.0, "preparing")
                        elif node_name == "generate_draft":
                            node_phase = "generating"
                            content_buffer = ""
                            gen_tracker.update(project_id, phase="generating", label="正在生成章节内容...", progress=30.0)
                            yield SSEResponse.progress("正在生成章节内容...", 30.0, "generating")
                        elif node_name == "save_generation_history":
                            node_phase = "saving"
                            gen_tracker.update(project_id, phase="saving", label="保存生成版本...", progress=85.0)
                            yield SSEResponse.progress("保存生成版本...", 85.0, "saving")

                    elif event_type == "on_chain_end":
                        node_name = event.get("name", "")
                        output = event.get("data", {}).get("output", {})
                        if node_name == "generate_draft" and isinstance(output, dict):
                            chapters = output.get("chapters", [])
                        if node_name == "generate_draft" and node_phase == "generating":
                            yield SSEResponse.progress("内容生成完成，保存中...", 82.0, "generating")
                        if node_name == "__interrupt__":
                            pass  # Human review interrupt — draft already generated

            except Exception as stream_err:
                err_name = type(stream_err).__name__
                if "Interrupt" not in err_name and "interrupt" not in str(stream_err).lower():
                    raise

            # Fallback: get final state
            if not chapters:
                try:
                    final_state = await subgraph.aget_state(config_ctx)
                    final_values = final_state.values if final_state else {}
                    chapters = final_values.get("chapters", [])
                except Exception:
                    pass

            # Auto-detect foreshadows from generated content
            cfg = get_gen_config(data)
            gen_chapter = chapters[0] if chapters else {}
            gen_content = gen_chapter.get("content", "")
            gen_idx = gen_chapter.get("chapter_index", 0)
            if gen_content:
                yield SSEResponse.progress("正在检测伏笔...", 92.0, "analyzing")
                fs_count = await _auto_extract_foreshadows(project_id, gen_idx, gen_content, cfg)
                if fs_count > 0:
                    yield SSEResponse.progress(f"检测到 {fs_count} 个伏笔", 95.0, "analyzing")

            gen_tracker.finish(project_id)
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
        chapter_index = result.get("current_chapter_index", 0)

        # Find the relevant analysis
        analysis = {}
        for a in chapter_analyses:
            if a.get("chapter_index") == chapter_index:
                analysis = a
                break

        return {"analysis": analysis, "status": "completed"}
    except Exception as e:
        logger.exception("Chapter analysis failed for %s", chapter_id)
        return {"status": "failed", "error": str(e)}


@router.post("/{chapter_id}/polish")
async def polish_chapter(chapter_id: str, data: dict):
    """Polish chapter prose via streaming AI, with real-time token output."""
    async def event_generator():
        try:
            content = data.get("content", "")
            if not content:
                yield SSEResponse.error("无章节内容")
                return

            yield SSEResponse.progress("正在准备润色...", 10.0, "polishing")

            # Build polish prompt using EditorAgent
            from app.agents.editor_agent import EditorAgent
            cfg = get_gen_config(data, temperature=0.5, max_tokens=8000)
            ai = create_ai_service(
                provider=cfg["provider"], api_key=cfg["api_key"],
                base_url=cfg["base_url"], model=cfg["model"],
                temperature=cfg["temperature"], max_tokens=cfg["max_tokens"],
            )
            editor = EditorAgent(model=ai.model)
            prompt = editor.build_polish_prompt(original_text=content)

            yield SSEResponse.progress("正在润色文本...", 30.0, "polishing")

            # Stream AI generation token-by-token
            polished = ""
            async for token in ai.generate_stream(editor.system_prompt, prompt):
                polished += token
                yield SSEResponse.chunk(token)

            yield SSEResponse.progress("正在保存...", 90.0, "polishing")

            # Sync polished content to DB
            chapter_index = data.get("chapter_index", 0)
            project_id = data.get("project_id", "")
            if project_id:
                from app.graphs.graph_db_sync import sync_chapter
                await sync_chapter(project_id, {
                    "chapter_index": chapter_index,
                    "content": polished.strip(),
                    "word_count": len(polished),
                    "status": "polished",
                })

            yield SSEResponse.progress("润色完成", 100.0, "complete")
            yield SSEResponse.result({"content": polished.strip(), "operation": "polish"})
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
    """Rewrite chapter based on user feedback via graph's rewrite_full node."""
    try:
        content = data.get("content", "")
        feedback = data.get("feedback", "请改善")

        chapter_index = data.get("chapter_index", 0)
        state = NovelState(
            project_id=data.get("project_id", ""),
            current_chapter_index=chapter_index,
            human_feedback=feedback,
            chapters=[{
                "chapter_index": chapter_index,
                "content": content,
            }],
            generation_config=get_gen_config(data),
        )

        from app.graphs.subgraphs.chapter_write import rewrite_full
        result = await rewrite_full(state)
        chapters_out = result.get("chapters", [])
        rewritten = chapters_out[0].get("content", "") if chapters_out else content

        return {"rewritten_content": rewritten, "status": "rewritten"}
    except Exception as e:
        logger.exception("Rewrite failed for %s", chapter_id)
        return {"status": "failed", "error": str(e)}


@router.post("/{chapter_id}/partial-regenerate-stream")
async def partial_regenerate_stream(chapter_id: str, data: dict):
    """Partial regenerate (rewrite selected text) via graph node with SSE streaming."""
    async def event_generator():
        try:
            selected_text = data.get("selected_text", "")
            strategy = data.get("strategy", "similar")
            custom_instruction = data.get("custom_instruction", "")

            if not selected_text:
                yield SSEResponse.error("未选中文本")
                return

            strategy_feedback = {
                "similar": "请保持原文风格重写以下段落。",
                "expand": "请在保持风格的基础上扩展细节和描写。",
                "condense": "请精简以下内容，去除冗余但保留核心信息。",
                "custom": f"请根据以下指令重写：{custom_instruction}",
            }
            feedback = strategy_feedback.get(strategy, strategy_feedback["similar"])

            yield SSEResponse.progress("正在重写选中段落...", 30.0, "rewriting")

            chapter_index = data.get("chapter_index", 0)
            state = NovelState(
                project_id=data.get("project_id", ""),
                current_chapter_index=chapter_index,
                human_feedback=f"{feedback}\n\n原文段落：{selected_text[:3000]}",
                chapters=[{
                    "chapter_index": chapter_index,
                    "content": selected_text,
                }],
                generation_config=get_gen_config(data, max_tokens=8000),
            )

            from app.graphs.subgraphs.chapter_write import rewrite_partial
            result = await rewrite_partial(state)
            chapters_out = result.get("chapters", [])
            partial_result = chapters_out[0].get("content", "") if chapters_out else selected_text

            # Stream back in chunks
            chunk_size = 100
            for i in range(0, len(partial_result), chunk_size):
                yield SSEResponse.chunk(partial_result[i:i + chunk_size])
                await asyncio.sleep(0.01)

            yield SSEResponse.result({"content": partial_result, "operation": "rewrite"})
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
