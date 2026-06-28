"""Book Import API — TXT/EPUB file upload, preview, and AI-powered structured import."""
import os
import re
import json
import asyncio
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.models.outline import Outline
from app.models.character import Character
from app.utils.sse_response import SSEResponse
from app.services.task_service import task_service
from app.graphs.subgraphs.book_import import create_book_import_subgraph
from app.logger import get_logger

router = APIRouter(prefix="/book-import", tags=["book_import"])
logger = get_logger(__name__)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Temp storage for uploaded book files (keyed by task_id)
_upload_store: dict[str, str] = {}  # task_id → raw_text


def _parse_epub_content(raw_bytes: bytes) -> str:
    """Extract text content from an EPUB file using ebooklib."""
    try:
        from ebooklib import epub
        import io
        book = epub.read_epub(io.BytesIO(raw_bytes))
        texts = []
        for item in book.get_items_of_type(9):  # ITEM_DOCUMENT = 9
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(item.get_body_content(), "html.parser")
            texts.append(soup.get_text(separator="\n"))
        return "\n\n".join(texts)
    except Exception as e:
        logger.warning("EPUB parsing failed, trying plain text: %s", e)
        return ""


@router.post("/upload")
async def upload_book(file: UploadFile = File(...), project_id: str = Form("")):
    """Upload a TXT/EPUB file for analysis. Max 50MB."""
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        return {"file_name": file.filename, "size": len(content),
                "error": "文件大小超过 50MB 限制", "task_id": ""}

    task_id = await task_service.create(
        project_id=project_id or "import",
        task_type="book_import",
        config={"file_name": file.filename, "file_size": len(content),
                "content_type": file.content_type or ""},
    )

    # Parse content based on file type
    filename_lower = file.filename.lower()
    raw_text = ""

    if filename_lower.endswith(".epub"):
        raw_text = _parse_epub_content(content)
    if not raw_text:
        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = content.decode("gbk")
            except Exception:
                raw_text = content.decode("utf-8", errors="replace")

    # Store parsed text in memory for the preview and apply endpoints
    _upload_store[task_id] = raw_text

    return {
        "file_name": file.filename,
        "size": len(content),
        "task_id": task_id,
        "format": "epub" if filename_lower.endswith(".epub") else "txt",
        "char_count": len(raw_text),
        "preview": raw_text[:500] + "..." if len(raw_text) > 500 else raw_text,
    }


@router.get("/preview/{task_id}")
async def get_preview(task_id: str):
    """Get import preview: detected chapters via regex + optional AI preview."""
    task = await task_service.get(task_id)
    if not task:
        return {"preview": {"chapters": [], "characters": []}, "error": "Task not found"}

    raw_text = _upload_store.get(task_id, "")
    if not raw_text:
        return {"preview": {"chapters": [], "characters": []}, "error": "Uploaded content expired or not found"}

    preview_text = raw_text[:10000]
    chapter_patterns = [
        r'第[一二三四五六七八九十百千\d]+章\s*[^\n]*',
        r'Chapter\s+\d+[^\n]*',
        r'第[一二三四五六七八九十百千\d]+节\s*[^\n]*',
        r'卷[一二三四五六七八九十百千\d]+\s*[^\n]*',
    ]
    chapters = []
    seen_positions = set()
    for pattern in chapter_patterns:
        for m in re.finditer(pattern, preview_text):
            if m.start() not in seen_positions:
                seen_positions.add(m.start())
                chapters.append({"title": m.group().strip()[:80], "position": m.start()})

    chapters.sort(key=lambda c: c["position"])

    return {
        "preview": {
            "chapters": chapters[:30],
            "characters": [],
            "total_bytes": task.get("config", {}).get("file_size", 0),
            "total_chars": len(raw_text),
        }
    }


@router.post("/apply")
async def apply_import(data: dict, db: AsyncSession = Depends(get_db)):
    """Apply the import — run LangGraph BookImport subgraph and persist results."""
    task_id = data.get("task_id", "")
    project_id = data.get("project_id", "")

    if not project_id:
        return {"status": "error", "error": "project_id required"}

    task = await task_service.get(task_id)
    if not task:
        return {"status": "error", "error": "Task not found"}

    raw_text = _upload_store.pop(task_id, "")
    if not raw_text:
        return {"status": "error", "error": "No text content to import"}

    try:
        state = {
            "project_id": project_id,
            "title": data.get("title", "导入小说"),
            "genre": data.get("genre", "玄幻"),
            "_import_raw_text": raw_text,
            "outlines": [],
            "characters": [],
            "current_phase": "start",
        }

        subgraph = create_book_import_subgraph()
        config_ctx = {"configurable": {"thread_id": f"book_import_{task_id}"}}
        result = await subgraph.ainvoke(state, config_ctx)

        outlines_data = result.get("outlines", [])
        for i, ol in enumerate(outlines_data):
            outline = Outline(
                project_id=project_id,
                volume=ol.get("volume", 1),
                chapter_index=ol.get("chapter_index", ol.get("chapter_num", i + 1)),
                title=ol.get("title", f"第{i+1}章"),
                summary=ol.get("summary", ""),
                key_points=ol.get("key_points", ""),
                mode="one-to-one",
                expansion_strategy="balanced",
            )
            db.add(outline)

        characters_data = result.get("characters", [])
        for char in characters_data:
            character = Character(
                project_id=project_id,
                name=char.get("name", "未知角色"),
                role_type=char.get("role_type", "supporting"),
                personality=char.get("personality", ""),
                background=char.get("background", ""),
            )
            db.add(character)

        await db.commit()

        return {"status": "applied", "project_id": project_id,
                "outlines_created": len(outlines_data),
                "characters_created": len(characters_data),
                "message": "Import applied to project"}
    except Exception as e:
        logger.exception("Import apply failed for %s", task_id)
        return {"status": "error", "error": str(e)}


@router.post("/apply-stream")
async def apply_import_stream(data: dict):
    """Apply import with LangGraph subgraph + SSE streaming progress."""
    async def event_generator():
        try:
            project_id = data.get("project_id", "")
            task_id = data.get("task_id", "")

            task = await task_service.get(task_id)
            if not task:
                yield SSEResponse.error("Task not found")
                return

            raw_text = _upload_store.pop(task_id, "")
            if not raw_text:
                yield SSEResponse.error("No text content")
                return

            state = {
                "project_id": project_id,
                "title": data.get("title", "导入小说"),
                "genre": data.get("genre", "玄幻"),
                "_import_raw_text": raw_text,
                "outlines": [],
                "characters": [],
                "current_phase": "start",
            }

            subgraph = create_book_import_subgraph()
            config_ctx = {"configurable": {"thread_id": f"book_import_stream_{task_id}"}}

            yield SSEResponse.progress("正在解析文件...", 10.0, "parsing")
            await asyncio.sleep(0.05)

            async for event in subgraph.astream(state, config_ctx):
                for node_name, node_output in event.items():
                    if node_name == "detect_chapter_boundaries":
                        chapters = node_output.get("_chapter_boundaries", [])
                        yield SSEResponse.progress(
                            f"检测到 {len(chapters)} 个章节边界", 40.0, "detecting",
                            chapters_found=len(chapters))
                    elif node_name == "extract_characters":
                        chars = node_output.get("_extracted_characters", [])
                        yield SSEResponse.progress(
                            f"提取到 {len(chars)} 个角色", 70.0, "extracting",
                            characters_found=len(chars))
                    elif node_name == "structure_content":
                        outlines = node_output.get("outlines", [])
                        characters = node_output.get("characters", [])
                        yield SSEResponse.progress(
                            f"结构化完成: {len(outlines)} 章, {len(characters)} 个角色",
                            90.0, "structuring")

            final = await subgraph.aget_state(config_ctx)
            values = final.values if final else {}
            outlines = values.get("outlines", [])
            characters = values.get("characters", [])

            yield SSEResponse.result({
                "outlines": outlines[:20],
                "characters": characters[:10],
                "total_outlines": len(outlines),
                "total_characters": len(characters),
            })
            yield SSEResponse.done(f"导入完成: {len(outlines)} 章, {len(characters)} 个角色")

        except Exception as e:
            logger.exception("Import stream failed")
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
