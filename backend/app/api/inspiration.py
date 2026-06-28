"""Inspiration Generation API — AI-powered creative idea generation via graph."""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.inspiration import Inspiration
from app.graphs.state import NovelState
from app.utils.sse_response import SSEResponse
from app.config import settings
from app.graphs.utils import get_gen_config
from app.logger import get_logger
import uuid
import asyncio

router = APIRouter(prefix="/inspiration", tags=["inspiration"])
logger = get_logger(__name__)


def _build_insp_state(data: dict) -> NovelState:
    """Build a minimal NovelState for inspiration generation."""
    return NovelState(
        project_id=data.get("project_id", ""),
        title=data.get("title", ""),
        genre=data.get("genre", data.get("genre_tags", "玄幻")),
        description=data.get("context", data.get("description", "")),
        world_setting=data.get("world_setting", {}),
        characters=data.get("characters", []),
        human_feedback=data.get("feedback", ""),
        generation_config=get_gen_config(data, temperature=0.9, max_tokens=8000),
    )


@router.post("/generate")
async def generate_inspiration(data: dict):
    """Generate creative inspiration ideas via graph's generate_options node."""
    from app.graphs.subgraphs.inspiration import generate_options

    state = _build_insp_state(data)
    try:
        result = await generate_options(state)
        inspirations = result.get("inspirations", [])
        return {"ideas": inspirations}
    except Exception as e:
        logger.error("Inspiration generation failed: %s", e)
        return {"ideas": [], "error": str(e)}


@router.post("/generate-stream")
async def generate_inspiration_stream(data: dict):
    """Generate inspiration with SSE streaming via graph node."""
    async def event_generator():
        try:
            from app.graphs.subgraphs.inspiration import generate_options

            yield SSEResponse.progress("正在生成创意灵感...", 20.0, "generating")

            state = _build_insp_state(data)
            result = await generate_options(state)
            inspirations = result.get("inspirations", [])

            yield SSEResponse.result({"ideas": inspirations})
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
    """Refine an existing inspiration based on feedback via graph node."""
    from app.graphs.subgraphs.inspiration import refine_iteration

    state = _build_insp_state(data)
    state["human_feedback"] = f"原始灵感：{data.get('original_idea', '')}\n用户反馈：{data.get('feedback', '请改进')}"

    try:
        result = await refine_iteration(state)
        inspirations = result.get("inspirations", [])
        latest = inspirations[-1] if inspirations else {}
        return {"refined": True, "idea": latest}
    except Exception as e:
        logger.error("Refine inspiration failed: %s", e)
        return {"refined": False, "error": str(e)}


@router.post("/quick-generate")
async def quick_generate(data: dict):
    """Quick single inspiration generation via graph node."""
    from app.graphs.subgraphs.inspiration import generate_options

    state = _build_insp_state(data)
    # Limit to a single quick idea
    state["generation_config"]["max_tokens"] = 2000
    state["human_feedback"] = "请只用一句话（50-100字）"

    try:
        result = await generate_options(state)
        inspirations = result.get("inspirations", [])
        first = inspirations[0].get("idea", "") if inspirations else ""
        return {"idea": first}
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
