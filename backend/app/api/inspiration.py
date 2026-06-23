"""Inspiration Generation API — AI-powered creative idea generation."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.inspiration import Inspiration
from app.services.ai_service import create_ai_service
from app.utils.sse_response import SSEResponse
from app.config import settings
from app.logger import get_logger
import uuid
import asyncio

router = APIRouter(prefix="/inspiration", tags=["inspiration"])
logger = get_logger(__name__)


@router.post("/generate")
async def generate_inspiration(data: dict):
    """Generate creative inspiration ideas via AI."""
    ai = create_ai_service(
        provider=data.get("provider", "openai"),
        api_key=data.get("api_key"),
        model=data.get("model", settings.default_ai_model),
        temperature=0.9, max_tokens=8000,
    )
    prompt = f"""你是一位创意写作顾问。请为以下需求生成3-5个创意灵感：

类型偏好：{data.get('genre_tags', '任意')}
上下文：{data.get('context', '无')}
反馈方向：{data.get('feedback', '')}

以JSON数组格式输出：
[{{"idea": "创意描述(50-200字)", "type": "情节转折/角色发展/世界观扩展/冲突设计/悬念设置", "genre_tags": ["标签"], "impact": "high/medium/low", "implementation": "实现建议"}}]
只输出JSON数组。"""

    try:
        result = await ai.generate_json("你是一位富有创造力的写作顾问。只输出JSON数组。", prompt)
        if isinstance(result, dict):
            result = [result]
        for insp in result:
            insp.setdefault("id", str(uuid.uuid4()))
        return {"ideas": result}
    except Exception as e:
        logger.error("Inspiration generation failed: %s", e)
        return {"ideas": [], "error": str(e)}


@router.post("/generate-stream")
async def generate_inspiration_stream(data: dict):
    """Generate inspiration with SSE streaming."""
    async def event_generator():
        try:
            ai = create_ai_service(
                provider=data.get("provider", "openai"),
                api_key=data.get("api_key"),
                model=data.get("model", settings.default_ai_model),
                temperature=0.9, max_tokens=8000,
            )
            yield SSEResponse.progress("正在生成创意灵感...", 20.0, "generating")

            prompt = f"""类型偏好：{data.get('genre_tags', '任意')}
上下文：{data.get('context', '无')}

请生成3-5个创意灵感点子，用JSON数组输出：
[{{"idea": "...", "type": "...", "genre_tags": [...], "impact": "...", "implementation": "..."}}]
只输出JSON数组。"""

            result = await ai.generate_json("你是一位创意写作顾问。只输出JSON数组。", prompt)
            if isinstance(result, dict):
                result = [result]
            for insp in result:
                insp.setdefault("id", str(uuid.uuid4()))

            yield SSEResponse.result({"ideas": result})
            yield SSEResponse.done("灵感生成完成")
        except Exception as e:
            logger.error("Inspiration stream failed: %s", e)
            yield SSEResponse.error(str(e))

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/refine")
async def refine_inspiration(data: dict):
    """Refine an existing inspiration based on feedback."""
    ai = create_ai_service(
        provider=data.get("provider", "openai"),
        api_key=data.get("api_key"),
        model=data.get("model", settings.default_ai_model),
        temperature=0.9, max_tokens=4000,
    )
    prompt = f"""原始灵感：{data.get('original_idea', '')}
用户反馈：{data.get('feedback', '请改进')}

请根据反馈改进这个创意灵感，以JSON格式输出：
{{"idea": "改进后的创意描述", "type": "...", "genre_tags": [...], "impact": "...", "implementation": "..."}}
只输出JSON。"""

    try:
        result = await ai.generate_json("你是一位创意写作顾问。只输出JSON。", prompt)
        return {"refined": True, "idea": result}
    except Exception as e:
        logger.error("Refine inspiration failed: %s", e)
        return {"refined": False, "error": str(e)}


@router.post("/quick-generate")
async def quick_generate(data: dict):
    """Quick single inspiration generation."""
    ai = create_ai_service(
        provider=data.get("provider", "openai"),
        api_key=data.get("api_key"),
        model=data.get("model", settings.default_ai_model),
        temperature=0.9, max_tokens=2000,
    )
    prompt = f"""请用一句话（50-100字）生成一个关于"{data.get('genre_tags', '小说')}"的创意点子。只输出纯文本。"""
    try:
        result = await ai.generate("你是一位创意作家。", prompt)
        return {"idea": result.strip()}
    except Exception as e:
        return {"idea": "", "error": str(e)}


@router.get("/saved")
async def list_saved_inspirations(db: AsyncSession = Depends(get_db)):
    """List saved inspirations from database."""
    result = await db.execute(select(Inspiration).order_by(Inspiration.created_at.desc()).limit(50))
    items = result.scalars().all()
    import json
    return {
        "items": [{
            "id": i.id, "idea": i.idea, "insp_type": i.insp_type,
            "genre_tags": json.loads(i.genre_tags) if i.genre_tags else [],
            "impact": i.impact, "implementation": i.implementation,
            "created_at": str(i.created_at),
        } for i in items],
        "total": len(items),
    }


@router.post("/save")
async def save_inspiration(data: dict, db: AsyncSession = Depends(get_db)):
    """Save an inspiration to the database."""
    import json
    insp = Inspiration(
        project_id=data.get("project_id"),
        idea=data.get("idea", ""),
        insp_type=data.get("insp_type", "情节转折"),
        genre_tags=json.dumps(data.get("genre_tags", []), ensure_ascii=False),
        impact=data.get("impact", "medium"),
        implementation=data.get("implementation", ""),
    )
    db.add(insp)
    await db.commit()
    await db.refresh(insp)
    return {"id": insp.id, "saved": True}


@router.post("/{inspiration_id}/convert-to-project")
async def convert_to_project(inspiration_id: str, db: AsyncSession = Depends(get_db)):
    """Convert an inspiration into a new project."""
    from app.models.project import Project
    result = await db.execute(select(Inspiration).where(Inspiration.id == inspiration_id))
    insp = result.scalar_one_or_none()
    if not insp:
        return {"project_id": "", "error": "Inspiration not found"}

    project = Project(
        title=f"灵感: {insp.idea[:30]}...",
        description=insp.idea[:200],
        genre="玄幻",
        status="planning",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return {"project_id": project.id, "message": "Project created from inspiration"}
