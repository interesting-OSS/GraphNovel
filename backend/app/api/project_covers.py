"""Project Cover Generation API — AI cover prompt generation + download."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.services.cover_service import CoverService
from app.services.ai_service import create_ai_service
from app.config import settings
from app.logger import get_logger
import json
import httpx

router = APIRouter(prefix="/projects", tags=["project_covers"])
logger = get_logger(__name__)


@router.post("/{project_id}/generate-cover")
async def generate_cover(project_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Generate a cover prompt + image via Qwen multimodal."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    world_setting = {}
    if project.world_setting:
        try:
            world_setting = json.loads(project.world_setting)
        except (json.JSONDecodeError, TypeError):
            pass

    world_summary = " ".join(
        world_setting.get(k, "")[:100]
        for k in ["time_period", "power_system", "factions", "culture"]
    )

    ai = create_ai_service(
        provider=data.get("provider", "openai"),
        api_key=data.get("api_key"),
        model=data.get("model", settings.default_ai_model),
        temperature=0.7, max_tokens=4000,
    )

    cover_service = CoverService(ai_service=ai)
    cover_result = await cover_service.generate_cover(
        title=project.title,
        description=project.description or "",
        genre=project.genre,
        world_summary=world_summary,
        style=data.get("style", "chinese"),
        provider=data.get("image_provider", settings.image_provider),
        size=data.get("size", "1024x1024"),
    )

    # Store results on project
    project.cover_prompt = cover_result["prompt"]
    if cover_result["url"]:
        project.cover_url = cover_result["url"]
    await db.commit()

    return {
        "cover_prompt": cover_result["prompt"],
        "cover_url": cover_result["url"],
        "message": cover_result["message"],
        "provider_used": cover_result["provider_used"],
        "error": cover_result.get("error"),
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
    from app.graphs.subgraphs.cover_gen import create_cover_subgraph
    result_proj = await db.execute(select(Project).where(Project.id == project_id))
    project = result_proj.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    subgraph = create_cover_subgraph()
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
