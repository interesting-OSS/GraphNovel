"""Celery task definitions — long-running async operations executed by workers.

Each task:
  1. Loads its config from the background_tasks DB record
  2. Executes the actual work (AI generation, analysis, etc.)
  3. Updates progress in the DB so the API can relay it to the frontend
"""
import asyncio
import json
import logging
from datetime import datetime
from sqlalchemy import select
from app.celery_app import app
from app.database import async_session_factory

logger = logging.getLogger(__name__)


async def _update_task_progress(task_id: str, progress: float, status: str = ""):
    """Update a background_tasks row with current progress."""
    from app.models.background_task import BackgroundTask
    async with async_session_factory() as session:
        result = await session.execute(
            select(BackgroundTask).where(BackgroundTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.progress = min(progress, 100.0)
            task.updated_at = datetime.now()
            if status:
                task.status = status
            await session.commit()
"""
找到数据库中那条后台任务记录
更新它的进度、时间和状态字段
让前端轮询时能看到实时进度。
"""

async def _mark_task_complete(task_id: str, result_data: dict | None = None):
    """Mark a task as completed with optional result payload."""
    from app.models.background_task import BackgroundTask
    async with async_session_factory() as session:
        result = await session.execute(
            select(BackgroundTask).where(BackgroundTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "completed"
            task.progress = 100.0
            task.result = json.dumps(result_data, ensure_ascii=False) if result_data else None
            task.updated_at = datetime.now()
            await session.commit()


async def _mark_task_failed(task_id: str, error: str):
    """Mark a task as failed with an error message."""
    from app.models.background_task import BackgroundTask
    async with async_session_factory() as session:
        result = await session.execute(
            select(BackgroundTask).where(BackgroundTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        if task:
            task.status = "failed"
            task.error_message = error
            task.updated_at = datetime.now()
            await session.commit()


async def _is_cancelled(task_id: str) -> bool:
    """Check whether the task has been cancelled."""
    from app.models.background_task import BackgroundTask
    async with async_session_factory() as session:
        result = await session.execute(
            select(BackgroundTask).where(BackgroundTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        return task.status == "cancelled" if task else True


# ── Batch Chapter Generation ──────────────────────────────────────────────


async def _run_batch_generate(task_id: str, project_id: str, config: dict):
    """Execute batch chapter generation."""
    from app.services.ai_service import create_ai_service
    from app.models.chapter import Chapter
    from app.models.outline import Outline

    chapter_indices = config.get("chapter_indices", [])
    if not chapter_indices:
        logger.warning("Batch generate task %s: empty chapter_indices", task_id)
        await _mark_task_complete(task_id, {"chapters_generated": 0, "warning": "No chapters specified"})
        return

    generation_config = config.get("generation_config", {})
    total = len(chapter_indices)

    ai = create_ai_service(**generation_config)

    async with async_session_factory() as session:
        outlines_result = await session.execute(
            select(Outline).where(
                Outline.project_id == project_id,
                Outline.chapter_num.in_(chapter_indices),
            ).order_by(Outline.chapter_num)
        )
        outlines = outlines_result.scalars().all()

        for i, outline in enumerate(outlines):
            if await _is_cancelled(task_id):
                return

            progress = (i / total) * 100 if total else 0
            await _update_task_progress(task_id, progress, "running")

            # Build writing prompt
            prompt = (
                f"根据以下大纲写一章小说：\n"
                f"章节标题：{outline.title}\n"
                f"章节摘要：{outline.summary or '无'}\n"
                f"关键要点：{outline.key_points or '无'}\n"
                f"目标字数：3000字"
            )

            content = await ai.generate("你是一位专业的小说作家。", prompt)

            # Save chapter
            existing = await session.execute(
                select(Chapter).where(
                    Chapter.project_id == project_id,
                    Chapter.chapter_index == outline.chapter_num,
                )
            )
            chapter = existing.scalar_one_or_none()
            if chapter:
                chapter.content = content
                chapter.word_count = len(content)
            else:
                chapter = Chapter(
                    project_id=project_id,
                    chapter_index=outline.chapter_num,
                    title=outline.title,
                    content=content,
                    word_count=len(content),
                    status="draft",
                )
                session.add(chapter)
            await session.commit()

    await _mark_task_complete(task_id, {"chapters_generated": total})


# ── Batch Chapter Analysis ────────────────────────────────────────────────


async def _run_batch_analyze(task_id: str, project_id: str, config: dict):
    """Execute batch chapter analysis."""
    from app.services.ai_service import create_ai_service
    from app.models.chapter import Chapter
    from app.models.memory import PlotAnalysis

    chapter_indices = config.get("chapter_indices", [])
    generation_config = config.get("generation_config", {})
    total = len(chapter_indices)

    ai = create_ai_service(**generation_config)

    async with async_session_factory() as session:
        chapters_result = await session.execute(
            select(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_index.in_(chapter_indices),
            )
        )
        chapters = chapters_result.scalars().all()

        for i, chapter in enumerate(chapters):
            if await _is_cancelled(task_id):
                return

            progress = (i / total) * 100 if total else 0
            await _update_task_progress(task_id, progress, "running")

            analysis_prompt = (
                "请分析以下章节：\n"
                f"章节内容（前2000字）：\n"
                f"{chapter.content[:2000] if chapter.content else ''}\n\n"
                "请以JSON格式输出分析结果：\n"
                '{"plot_points": [], "conflict_info": {}, "emotional_arc": {}, '
                '"pacing_score": 0, "engagement_score": 0, "coherence_score": 0, '
                '"quality_score": 0, "suggestions": [], "report": "分析报告文本"}'
            )

            result = await ai.generate_json("你是一位文学分析专家。只输出JSON。", analysis_prompt)
            if not isinstance(result, dict):
                result = {}

            analysis = PlotAnalysis(
                project_id=project_id,
                chapter_id=chapter.id,
                plot_points=json.dumps(result.get("plot_points", []), ensure_ascii=False),
                conflict_info=json.dumps(result.get("conflict_info", {}), ensure_ascii=False),
                emotional_arc=json.dumps(result.get("emotional_arc", {}), ensure_ascii=False),
                pacing_score=result.get("pacing_score", 0),
                engagement_score=result.get("engagement_score", 0),
                coherence_score=result.get("coherence_score", 0),
                quality_score=result.get("quality_score", 0),
                suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
                report=result.get("report", ""),
            )
            session.add(analysis)
            await session.commit()

    await _mark_task_complete(task_id, {"chapters_analyzed": total})


# ── Batch Polish ──────────────────────────────────────────────────────────


async def _run_batch_polish(task_id: str, project_id: str, config: dict):
    """Execute batch chapter polish."""
    from app.services.ai_service import create_ai_service
    from app.models.chapter import Chapter

    chapter_indices = config.get("chapter_indices", [])
    generation_config = config.get("generation_config", {})
    total = len(chapter_indices)

    ai = create_ai_service(**generation_config)

    async with async_session_factory() as session:
        chapters_result = await session.execute(
            select(Chapter).where(
                Chapter.project_id == project_id,
                Chapter.chapter_index.in_(chapter_indices),
            )
        )
        chapters = chapters_result.scalars().all()

        for i, chapter in enumerate(chapters):
            if await _is_cancelled(task_id):
                return

            progress = (i / total) * 100 if total else 0
            await _update_task_progress(task_id, progress, "running")

            polished = await ai.generate(
                "你是资深文学编辑，请在不改变情节的前提下润色文字，提升文笔。",
                f"原文：\n{chapter.content}"
            )
            chapter.content = polished
            chapter.word_count = len(polished)
            chapter.status = "polished"
            await session.commit()

    await _mark_task_complete(task_id, {"chapters_polished": total})


# ── Book Import ───────────────────────────────────────────────────────────


async def _run_book_import(task_id: str, project_id: str, config: dict):
    """Execute book import: parse file, detect chapters, structure content."""
    from app.services.ai_service import create_ai_service
    from app.models.chapter import Chapter
    import os

    file_path = config.get("file_path", "")
    generation_config = config.get("generation_config", {})
    import_mode = config.get("import_mode", "full")

    if not file_path or not os.path.exists(file_path):
        await _mark_task_failed(task_id, f"File not found: {file_path}")
        return

    await _update_task_progress(task_id, 5, "running")

    # Parse file
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        raw_text = f.read()

    await _update_task_progress(task_id, 15, "running")

    # Use AI to detect chapter boundaries
    if len(raw_text) > 8000:
        sample = raw_text[:4000] + "\n...(中间内容省略)...\n" + raw_text[-4000:]
    else:
        sample = raw_text

    ai = create_ai_service(**generation_config)

    boundaries_prompt = (
        "请分析以下小说文本，识别所有章节的边界。对每个章节输出：\n"
        "- 章节序号\n"
        "- 章节标题（如果能识别）\n"
        "- 起始位置的关键词（文本前20字）\n\n"
        f"文本：\n{sample}\n\n"
        '以JSON数组格式输出：[{"index": 1, "title": "第1章 xxx", "keyword": "开头20字"}, ...]'
    )

    try:
        boundaries = await ai.generate_json("你是文本分析专家。只输出JSON数组。", boundaries_prompt)
    except Exception as e:
        await _mark_task_failed(task_id, f"Chapter boundary detection failed: {e}")
        return

    await _update_task_progress(task_id, 50, "running")

    # Split text by detected boundaries and extract actual content
    chapters_data = _split_by_boundaries(raw_text, boundaries, import_mode)

    async with async_session_factory() as session:
        total = len(chapters_data)
        for i, ch_data in enumerate(chapters_data):
            if await _is_cancelled(task_id):
                return

            chapter = Chapter(
                project_id=project_id,
                chapter_index=ch_data["chapter_index"],
                title=ch_data["title"],
                content=ch_data["content"],
                word_count=len(ch_data["content"]),
                status="draft",
            )
            session.add(chapter)
            await session.commit()

            progress = 50 + int((i + 1) / total * 50) if total else 100
            await _update_task_progress(task_id, progress, "running")

    await _mark_task_complete(task_id, {"chapters_imported": len(chapters_data)})


# ── Book Import Helpers ──────────────────────────────────────────────────


def _split_by_boundaries(raw_text: str, boundaries: list[dict], import_mode: str) -> list[dict]:
    """Split raw text into chapters using detected boundary keywords.

    Strategy:
      1. For each boundary, find its keyword in the raw text to locate the
         chapter start position.
      2. Extract content from that position to the next boundary's start.
      3. Fall back to regex patterns like "第N章" if keyword match fails.
    """
    import re

    if not boundaries:
        return [{"title": "全文", "chapter_index": 1, "content": raw_text}]

    # Build sorted list of (position, boundary) pairs
    positions = []
    for b in boundaries:
        keyword = (b.get("keyword", "") or "").strip()
        pos = _find_position(raw_text, keyword, b.get("index", len(positions) + 1))
        positions.append((pos, b))

    # Sort by position, filter out unfound entries
    positions.sort(key=lambda x: x[0])

    # Extract content between consecutive boundaries
    chapters = []
    for i, (pos, boundary) in enumerate(positions):
        title = boundary.get("title", f"第{boundary.get('index', i + 1)}章")
        chapter_index = boundary.get("index", i + 1)

        # Determine end position
        if i + 1 < len(positions):
            end_pos = positions[i + 1][0]
        else:
            end_pos = len(raw_text)

        content = raw_text[pos:end_pos].strip()

        # Skip empty chapters
        if not content:
            continue

        chapters.append({
            "title": title,
            "chapter_index": chapter_index,
            "content": content[:50000],  # Cap at ~50K chars per chapter
        })

    # If tail mode: only import the last N chapters
    if import_mode == "tail" and len(chapters) > 5:
        chapters = chapters[-5:]

    return chapters


def _find_position(raw_text: str, keyword: str, chapter_index: int) -> int:
    """Find the character position of a keyword in raw text.

    Falls back to regex chapter-title patterns if keyword match fails.
    """
    import re

    # Try exact keyword match (first 20 chars of chapter content)
    if keyword and len(keyword) >= 3:
        idx = raw_text.find(keyword)
        if idx >= 0:
            return idx

    # Fallback: regex for "第N章" pattern
    patterns = [
        rf"第\s*{chapter_index}\s*章",
        rf"第\s*[零一二三四五六七八九十百千]+\s*章",
    ]
    for pat in patterns:
        m = re.search(pat, raw_text)
        if m:
            return m.start()

    # Last resort: proportional position in text
    return 0


# ── Celery Task Wrappers ──────────────────────────────────────────────────


@app.task(bind=True, name="batch_generate")
def run_batch_generate(self, task_id: str, project_id: str, config: dict):
    """Celery task: batch chapter generation."""
    try:
        asyncio.run(_run_batch_generate(task_id, project_id, config))
    except Exception as e:
        logger.exception("Batch generate task %s failed", task_id)
        asyncio.run(_mark_task_failed(task_id, str(e)))
        raise


@app.task(bind=True, name="batch_analyze")
def run_batch_analyze(self, task_id: str, project_id: str, config: dict):
    """Celery task: batch chapter analysis."""
    try:
        asyncio.run(_run_batch_analyze(task_id, project_id, config))
    except Exception as e:
        logger.exception("Batch analyze task %s failed", task_id)
        asyncio.run(_mark_task_failed(task_id, str(e)))
        raise


@app.task(bind=True, name="batch_polish")
def run_batch_polish(self, task_id: str, project_id: str, config: dict):
    """Celery task: batch chapter polish."""
    try:
        asyncio.run(_run_batch_polish(task_id, project_id, config))
    except Exception as e:
        logger.exception("Batch polish task %s failed", task_id)
        asyncio.run(_mark_task_failed(task_id, str(e)))
        raise


@app.task(bind=True, name="book_import")
def run_book_import(self, task_id: str, project_id: str, config: dict):
    """Celery task: book file import and structuring."""
    try:
        asyncio.run(_run_book_import(task_id, project_id, config))
    except Exception as e:
        logger.exception("Book import task %s failed", task_id)
        asyncio.run(_mark_task_failed(task_id, str(e)))
        raise
