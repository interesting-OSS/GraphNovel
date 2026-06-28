"""Project Cover Generation API — AI cover prompt generation + download via graph."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.graphs.state import NovelState
from app.services.cover_service import CoverService
from app.config import settings
from app.graphs.utils import get_gen_config
from app.logger import get_logger
import json
import httpx

router = APIRouter(prefix="/projects", tags=["project_covers"])
logger = get_logger(__name__)


@router.post("/{project_id}/generate-cover")
async def generate_cover(project_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Generate a cover prompt via graph's cover_gen.generate_prompt node."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.graphs.subgraphs.cover_gen import generate_prompt

    world_setting = {}
    if project.world_setting:
        try:
            world_setting = json.loads(project.world_setting)
        except (json.JSONDecodeError, TypeError):
            pass

    state = NovelState(
        project_id=project_id,
        title=project.title,
        genre=project.genre,
        description=project.description or "",
        world_setting=world_setting,
        cover_prompt=data.get("prompt", ""),
        generation_config=get_gen_config(data, max_tokens=4000),
    )

    graph_result = await generate_prompt(state)
    cover_prompt = graph_result.get("cover_prompt", "")
    cover_data = graph_result.get("_cover_data", {})

    # Store on project
    if cover_prompt:
        project.cover_prompt = cover_prompt
        await db.commit()

    return {
        "cover_prompt": cover_prompt,
        "cover_url": project.cover_url,
        "message": "Cover prompt generated via graph",
        "style": cover_data.get("style", ""),
        "mood": cover_data.get("mood", ""),
    }


@router.get("/{project_id}/download-cover")
async def download_cover(project_id: str, db: AsyncSession = Depends(get_db)):
    """Download the generated cover image or its prompt data."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.cover_url:
        # If there's an actual URL, redirect or return it
        import httpx
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(project.cover_url)
                if resp.status_code == 200:
                    return Response(content=resp.content, media_type=resp.headers.get("content-type", "image/png"))
        except Exception:
            pass

    # Return prompt as JSON if no image available
    return {
        "cover_prompt": project.cover_prompt,
        "cover_url": project.cover_url,
        "message": "封面提示词已生成。图像需调用 DALL-E / Stable Diffusion 等图像模型生成后回填 cover_url。",
        "suggested_prompt": project.cover_prompt,
    }


@router.get("/cover-styles")
async def get_cover_styles():
    """Get available cover generation styles."""
    return {"styles": CoverService.get_available_styles()}


@router.post("/{project_id}/generate-cover-subgraph")
async def generate_cover_via_subgraph(project_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Generate cover via LangGraph CoverGenSubGraph: prompt → image → store."""
    from app.graphs.subgraphs.cover_gen import create_cover_gen_subgraph
    result_proj = await db.execute(select(Project).where(Project.id == project_id))
    project = result_proj.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    subgraph = create_cover_gen_subgraph()
    state = {
        "project_id": project_id,
        "title": project.title,
        "genre": project.genre,
        "world_setting": json.loads(project.world_setting) if project.world_setting else {},
        "description": project.description,
        "cover_prompt": data.get("prompt", ""),
    }
    result = await subgraph.ainvoke(state)

    # Persist cover prompt to DB
    cover_prompt = result.get("cover_prompt", "")
    if cover_prompt:
        project.cover_prompt = cover_prompt
        await db.commit()

    return {
        "cover_prompt": cover_prompt,
        "cover_url": result.get("cover_url", ""),
        "message": "Cover subgraph completed",
    }
