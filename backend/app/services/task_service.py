"""Background task service — async queue-based, replaces Celery.

Uses PerUserTaskQueue for in-process task execution:
  - Per-user FIFO: same user's tasks run sequentially
  - Different users can run concurrently
  - Progress persisted to PostgreSQL for API polling

Lifecycle:  pending → running → completed / failed
                            ↘ cancelled
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import select
from app.database import async_session_factory
from app.models.background_task import BackgroundTask
from app.tasks.task_queue import Task, TaskStatus, TaskProgressTracker, queue_manager
from app.logging_config import get_logger

logger = get_logger(__name__)


class TaskService:
    """Manages background task lifecycle via async queue + PostgreSQL."""

    async def create(
        self,
        project_id: str,
        task_type: str,
        config: dict,
        user_id: str = "default",
    ) -> str:
        """Create a task record and enqueue it.

        Returns the task ID for status polling.
        """
        async with async_session_factory() as session:
            task_record = BackgroundTask(
                project_id=project_id,
                task_type=task_type,
                status="pending",
                progress=0.0,
                config=json.dumps(config, ensure_ascii=False),
                can_pause=task_type in ("batch_generate", "batch_analyze", "batch_polish"),
                can_cancel=True,
            )
            session.add(task_record)
            await session.commit()
            task_id = task_record.id

        async_task = Task(
            id=task_id,
            user_id=user_id,
            coro=self._execute(task_id, project_id, task_type, config),
        )
        position = await queue_manager.enqueue(user_id, async_task)
        logger.info("Task %s enqueued (type=%s, position=%d)", task_id[:8], task_type, position)

        return task_id

    async def _execute(self, task_id: str, project_id: str, task_type: str, config: dict):
        """Execute a task based on its type."""
        tracker = TaskProgressTracker(Task(id=task_id, user_id=""))

        try:
            await tracker.start()

            if task_type == "batch_generate":
                await self._run_batch_generate(task_id, project_id, config, tracker)
            elif task_type == "batch_analyze":
                await self._run_batch_analyze(task_id, project_id, config, tracker)
            elif task_type == "batch_polish":
                await self._run_batch_polish(task_id, project_id, config, tracker)
            elif task_type == "book_import":
                await self._run_book_import(task_id, project_id, config, tracker)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

            await tracker.complete()
            await self._update_db(task_id, status="completed", progress=100.0)
        except Exception as e:
            await tracker.error(str(e))
            await self._update_db(task_id, status="failed", error=str(e))
            logger.exception("Task %s failed", task_id[:8])

    async def _run_batch_generate(self, task_id, project_id, config, tracker):
        """Batch chapter generation."""
        from app.services.ai_service import create_ai_service
        from app.models.chapter import Chapter
        from app.models.outline import Outline

        chapter_indices = config.get("chapter_indices", [])
        if not chapter_indices:
            return

        gen_config = config.get("generation_config", {})
        total = len(chapter_indices)
        ai = create_ai_service(**gen_config)

        async with async_session_factory() as session:
            outlines_result = await session.execute(
                select(Outline).where(
                    Outline.project_id == project_id,
                    Outline.chapter_index.in_(chapter_indices),
                ).order_by(Outline.chapter_index)
            )
            outlines = outlines_result.scalars().all()

            for i, outline in enumerate(outlines):
                if await self._is_cancelled(task_id):
                    return
                await tracker.generating(current_chars=i * 3000, estimated_total=total * 3000)

                prompt = (
                    f"根据以下大纲写一章小说：\n"
                    f"章节标题：{outline.title}\n"
                    f"章节摘要：{outline.summary or '无'}\n"
                    f"关键要点：{outline.key_points or '无'}\n"
                    f"目标字数：3000字"
                )
                content = await ai.generate("你是一位专业的小说作家。", prompt)

                existing = await session.execute(
                    select(Chapter).where(
                        Chapter.project_id == project_id,
                        Chapter.chapter_index == outline.chapter_index,
                    )
                )
                chapter = existing.scalar_one_or_none()
                if chapter:
                    chapter.content = content
                    chapter.word_count = len(content)
                else:
                    session.add(Chapter(
                        project_id=project_id, chapter_index=outline.chapter_index,
                        title=outline.title, content=content,
                        word_count=len(content), status="draft",
                    ))
                await session.commit()

    async def _run_batch_analyze(self, task_id, project_id, config, tracker):
        """Batch chapter analysis."""
        from app.services.ai_service import create_ai_service
        from app.models.chapter import Chapter
        from app.models.memory import PlotAnalysis

        chapter_indices = config.get("chapter_indices", [])
        gen_config = config.get("generation_config", {})
        total = len(chapter_indices)
        ai = create_ai_service(**gen_config)

        async with async_session_factory() as session:
            chapters_result = await session.execute(
                select(Chapter).where(
                    Chapter.project_id == project_id,
                    Chapter.chapter_index.in_(chapter_indices),
                )
            )
            chapters = chapters_result.scalars().all()

            for i, chapter in enumerate(chapters):
                if await self._is_cancelled(task_id):
                    return
                await tracker.generating(current_chars=i, estimated_total=total)

                result = await ai.generate_json(
                    "你是一位文学分析专家。只输出JSON。",
                    f"请分析以下章节（前2000字）：\n{chapter.content[:2000] if chapter.content else ''}\n\n"
                    '{"plot_points":[],"conflict_info":{},"emotional_arc":{},'
                    '"pacing_score":0,"engagement_score":0,"coherence_score":0,'
                    '"quality_score":0,"suggestions":[],"report":"分析报告文本"}'
                )
                if not isinstance(result, dict):
                    result = {}

                session.add(PlotAnalysis(
                    project_id=project_id, chapter_id=chapter.id,
                    plot_points=json.dumps(result.get("plot_points", []), ensure_ascii=False),
                    conflict_info=json.dumps(result.get("conflict_info", {}), ensure_ascii=False),
                    emotional_arc=json.dumps(result.get("emotional_arc", {}), ensure_ascii=False),
                    pacing_score=result.get("pacing_score", 0),
                    engagement_score=result.get("engagement_score", 0),
                    coherence_score=result.get("coherence_score", 0),
                    quality_score=result.get("quality_score", 0),
                    suggestions=json.dumps(result.get("suggestions", []), ensure_ascii=False),
                    report=result.get("report", ""),
                ))
                await session.commit()

    async def _run_batch_polish(self, task_id, project_id, config, tracker):
        """Batch chapter polish."""
        from app.services.ai_service import create_ai_service
        from app.models.chapter import Chapter

        chapter_indices = config.get("chapter_indices", [])
        gen_config = config.get("generation_config", {})
        total = len(chapter_indices)
        ai = create_ai_service(**gen_config)

        async with async_session_factory() as session:
            chapters_result = await session.execute(
                select(Chapter).where(
                    Chapter.project_id == project_id,
                    Chapter.chapter_index.in_(chapter_indices),
                )
            )
            chapters = chapters_result.scalars().all()

            for i, chapter in enumerate(chapters):
                if await self._is_cancelled(task_id):
                    return
                await tracker.generating(current_chars=i, estimated_total=total)
                polished = await ai.generate(
                    "你是资深文学编辑，请在不改变情节的前提下润色文字。",
                    f"原文：\n{chapter.content}"
                )
                chapter.content = polished
                chapter.word_count = len(polished)
                chapter.status = "polished"
                await session.commit()

    async def _run_book_import(self, task_id, project_id, config, tracker):
        """Book file import."""
        from app.services.ai_service import create_ai_service
        from app.models.chapter import Chapter
        import os

        file_path = config.get("file_path", "")
        gen_config = config.get("generation_config", {})
        if not file_path or not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        await tracker.loading("Reading file...")
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            raw_text = f.read()

        await tracker.preparing("Detecting chapters...")
        ai = create_ai_service(**gen_config)
        sample = raw_text if len(raw_text) <= 8000 else raw_text[:4000] + "\n...(truncated)...\n" + raw_text[-4000:]

        boundaries = await ai.generate_json(
            "你是文本分析专家。只输出JSON数组。",
            f"请识别小说章节边界。文本：\n{sample}\n\n"
            '[{"index":1,"title":"第1章 xxx","keyword":"开头20字"},...]'
        )

        await tracker.generating(current_chars=50, estimated_total=100)
        chapters_data = _split_by_boundaries(raw_text, boundaries, config.get("import_mode", "full"))

        async with async_session_factory() as session:
            for i, ch in enumerate(chapters_data):
                if await self._is_cancelled(task_id):
                    return
                session.add(Chapter(
                    project_id=project_id, chapter_index=ch["chapter_index"],
                    title=ch["title"], content=ch["content"][:50000],
                    word_count=len(ch["content"]), status="draft",
                ))
                await session.commit()
                await tracker.saving(f"Saving chapter {i+1}/{len(chapters_data)}...", sub_progress=(i+1)/max(len(chapters_data), 1))

    # ── Helpers ─────────────────────────────────────────────────────────

    @staticmethod
    async def _update_db(task_id: str, **kwargs):
        """Update a task record in the database."""
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if task:
                for key, value in kwargs.items():
                    setattr(task, key, value)
                task.updated_at = datetime.now(timezone.utc)
                await session.commit()

    @staticmethod
    async def _is_cancelled(task_id: str) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask.status).where(BackgroundTask.id == task_id)
            )
            status = result.scalar_one_or_none()
            return status == "cancelled" if status else True

    async def get(self, task_id: str) -> Optional[dict]:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            return self._to_dict(task) if task else None

    async def list(self, project_id: Optional[str] = None) -> list[dict]:
        async with async_session_factory() as session:
            stmt = select(BackgroundTask).order_by(BackgroundTask.created_at.desc()).limit(100)
            if project_id:
                stmt = stmt.where(BackgroundTask.project_id == project_id)
            result = await session.execute(stmt)
            return [self._to_dict(t) for t in result.scalars().all()]

    async def cancel(self, task_id: str) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task or not task.can_cancel or task.status not in ("pending", "running", "paused"):
                return False
            task.status = "cancelled"
            task.updated_at = datetime.now(timezone.utc)
            await session.commit()
            return True

    async def delete(self, task_id: str) -> bool:
        async with async_session_factory() as session:
            result = await session.execute(
                select(BackgroundTask).where(BackgroundTask.id == task_id)
            )
            task = result.scalar_one_or_none()
            if not task or task.status not in ("completed", "failed", "cancelled"):
                return False
            await session.delete(task)
            await session.commit()
            return True

    async def cleanup_stale(self):
        """Reset stale pending/running tasks on startup."""
        async with async_session_factory() as session:
            from app.tasks.stale_task_reset import reset_stale_tasks
            await reset_stale_tasks(session)

    @staticmethod
    def _to_dict(task: BackgroundTask) -> dict:
        return {
            "id": task.id,
            "project_id": task.project_id,
            "task_type": task.task_type,
            "status": task.status,
            "progress": task.progress,
            "config": json.loads(task.config) if task.config else {},
            "result": json.loads(task.result) if task.result else None,
            "error_message": task.error_message,
            "can_pause": task.can_pause,
            "can_cancel": task.can_cancel,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "updated_at": task.updated_at.isoformat() if task.updated_at else None,
        }


# ── Book import helpers ──────────────────────────────────────────────────────

def _find_position(raw_text: str, keyword: str, chapter_index: int) -> int:
    """Find the character position of a keyword in raw text.

    Falls back to regex chapter-title patterns if keyword match fails.
    """
    import re
    if keyword and len(keyword) >= 3:
        idx = raw_text.find(keyword)
        if idx >= 0:
            return idx
    patterns = [
        rf"第\s*{chapter_index}\s*章",
        rf"第\s*[零一二三四五六七八九十百千]+\s*章",
    ]
    for pat in patterns:
        m = re.search(pat, raw_text)
        if m:
            return m.start()
    return 0


def _split_by_boundaries(raw_text: str, boundaries: list[dict], import_mode: str) -> list[dict]:
    """Split raw text into chapters using detected boundary keywords with regex fallback."""
    if not boundaries:
        return [{"title": "全文", "chapter_index": 1, "content": raw_text}]

    positions = []
    for b in boundaries:
        keyword = (b.get("keyword", "") or "").strip()
        idx = _find_position(raw_text, keyword, b.get("index", len(positions) + 1))
        positions.append((idx, b))

    positions.sort(key=lambda x: x[0])
    chapters = []
    for i, (pos, boundary) in enumerate(positions):
        end_pos = positions[i + 1][0] if i + 1 < len(positions) else len(raw_text)
        content = raw_text[pos:end_pos].strip()
        if not content:
            continue
        chapters.append({
            "title": boundary.get("title", f"第{boundary.get('index', i+1)}章"),
            "chapter_index": boundary.get("index", i + 1),
            "content": content[:50000],
        })

    if import_mode == "tail" and len(chapters) > 5:
        chapters = chapters[-5:]
    return chapters


# Singleton
task_service = TaskService()
