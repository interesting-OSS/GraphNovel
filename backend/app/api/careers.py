"""Career API routes — CRUD for career/level systems with AI generation via graph."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.relationship import Career
from app.graphs.state import NovelState
from app.graphs.utils import get_gen_config
from app.config import settings
from app.logger import get_logger
import json

router = APIRouter(prefix="/careers", tags=["careers"])
logger = get_logger(__name__)


@router.get("/project/{project_id}")
async def list_careers(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all careers for a project."""
    result = await db.execute(select(Career).where(Career.project_id == project_id))
    careers = result.scalars().all()
    return {
        "items": [{
            "id": c.id, "name": c.name, "career_type": c.career_type,
            "description": c.description,
            "levels": json.loads(c.levels) if c.levels else [],
        } for c in careers],
        "total": len(careers),
    }


@router.get("/{career_id}")
async def get_career(career_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Career).where(Career.id == career_id))
    career = result.scalar_one_or_none()
    if not career:
        raise HTTPException(status_code=404, detail="Career not found")
    return {
        "id": career.id, "project_id": career.project_id,
        "name": career.name, "career_type": career.career_type,
        "description": career.description,
        "levels": json.loads(career.levels) if career.levels else [],
    }


@router.post("")
async def create_career(data: dict, db: AsyncSession = Depends(get_db)):
    career = Career(
        project_id=data.get("project_id", ""),
        name=data.get("name", "新职业"),
        career_type=data.get("career_type", "主要职业"),
        description=data.get("description", ""),
        levels=json.dumps(data.get("levels", []), ensure_ascii=False) if data.get("levels") else None,
    )
    db.add(career)
    await db.commit()
    await db.refresh(career)
    return {"id": career.id}


@router.put("/{career_id}")
async def update_career(career_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Career).where(Career.id == career_id))
    career = result.scalar_one_or_none()
    if not career:
        raise HTTPException(status_code=404, detail="Career not found")
    if "name" in data:
        career.name = data["name"]
    if "career_type" in data:
        career.career_type = data["career_type"]
    if "description" in data:
        career.description = data["description"]
    if "levels" in data:
        career.levels = json.dumps(data["levels"], ensure_ascii=False)
    await db.commit()
    return {"id": career_id, "updated": True}


@router.delete("/{career_id}")
async def delete_career(career_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Career).where(Career.id == career_id))
    career = result.scalar_one_or_none()
    if not career:
        raise HTTPException(status_code=404, detail="Career not found")
    await db.delete(career)
    await db.commit()
    return {"deleted": True}


@router.post("/generate")
async def generate_career(data: dict):
    """Generate career systems via the graph's career_manage_node."""
    from app.graphs.main_graph import career_manage_node

    state = NovelState(
        project_id=data.get("project_id", ""),
        genre=data.get("genre", "玄幻"),
        world_setting=data.get("world_setting", {}),
        generation_config=get_gen_config(data, max_tokens=8000),
    )

    try:
        result = await career_manage_node(state)
        return {"status": "completed", "careers": result.get("careers", [])}
    except Exception as e:
        logger.error("Career generation failed: %s", e)
        return {"status": "failed", "error": str(e)}
