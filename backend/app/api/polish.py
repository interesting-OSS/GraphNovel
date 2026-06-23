"""Text Polish API — AI prose polishing with streaming support."""
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.utils.sse_response import SSEResponse
from app.services.ai_service import create_ai_service
from app.config import settings
from app.logger import get_logger
import asyncio

router = APIRouter(prefix="/polish", tags=["polish"])
logger = get_logger(__name__)


@router.post("/text")
async def polish_text(data: dict):
    """Polish text via AI (non-streaming)."""
    ai = create_ai_service(
        provider=data.get("provider", "openai"),
        api_key=data.get("api_key"),
        model=data.get("model", settings.default_ai_model),
        temperature=0.5, max_tokens=32000,
    )
    content = data.get("content", "")
    if not content:
        return {"polished_text": "", "error": "No content provided"}

    prompt = f"""你是一位资深小说编辑。请润色以下文本，优化语言流畅度、用词精准度和节奏把控。
保持原文风格和情节不变，只做文笔层面的优化。

原文：
{content[:15000]}

请输出润色后的完整文本："""

    try:
        result = await ai.generate("你是一位资深小说编辑。", prompt)
        return {"polished_text": result.strip()}
    except Exception as e:
        logger.error("Polish text failed: %s", e)
        return {"polished_text": "", "error": str(e)}


@router.post("/text-stream")
async def polish_text_stream(data: dict):
    """Polish text with SSE streaming."""
    async def event_generator():
        try:
            ai = create_ai_service(
                provider=data.get("provider", "openai"),
                api_key=data.get("api_key"),
                model=data.get("model", settings.default_ai_model),
                temperature=0.5, max_tokens=32000,
            )
            content = data.get("content", "")
            if not content:
                yield SSEResponse.error("无文本内容")
                return

            yield SSEResponse.progress("正在润色文本...", 20.0, "polishing")

            prompt = f"""你是一位资深小说编辑。请润色以下文本，优化语言流畅度、用词精准度和节奏把控。
保持原文风格和情节不变，只做文笔层面的优化。

原文：
{content[:15000]}

请输出润色后的完整文本："""

            full_response = ""
            async for chunk in ai.generate_stream("你是一位资深小说编辑。", prompt):
                full_response += chunk
                yield SSEResponse.chunk(chunk)

            yield SSEResponse.result({"polished_text": full_response})
            yield SSEResponse.done("润色完成")
        except Exception as e:
            logger.error("Polish stream failed: %s", e)
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/batch")
async def polish_batch(data: dict):
    """Create a background batch polish task."""
    from app.services.task_service import task_service
    task_id = await task_service.create(
        project_id=data.get("project_id", ""),
        task_type="batch_polish",
        config={"chapter_ids": data.get("chapter_ids", []), "provider": data.get("provider", "openai")},
    )
    return {"task_id": task_id, "message": "批量润色任务已创建"}
