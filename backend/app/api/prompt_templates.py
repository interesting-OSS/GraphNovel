"""Prompt Template Management API — CRUD for reusable prompt templates."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.prompt_template import PromptTemplate
from app.logger import get_logger
from app.constants import CATEGORY_LIST, POPULAR_TAGS

router = APIRouter(prefix="/prompt-templates", tags=["prompt_templates"])
logger = get_logger(__name__)

BUILTIN_CATEGORIES = ["世界观", "角色", "大纲", "写作", "润色", "分析", "通用"]
GENRE_CATEGORIES = CATEGORY_LIST


@router.get("")
async def list_templates(category: str = "", db: AsyncSession = Depends(get_db)):
    """List prompt templates, optionally filtered by category."""
    query = select(PromptTemplate)
    if category:
        query = query.where(PromptTemplate.category == category)
    result = await db.execute(query)
    templates = result.scalars().all()
    return {
        "items": [{
            "id": t.id, "name": t.name, "category": t.category,
            "description": t.description, "content": t.content,
            "is_builtin": t.is_builtin,
        } for t in templates],
        "categories": BUILTIN_CATEGORIES,
        "total": len(templates),
    }


@router.get("/categories")
async def list_categories():
    """List all prompt template categories."""
    return {"categories": BUILTIN_CATEGORIES, "genre_categories": GENRE_CATEGORIES}


@router.post("")
async def create_template(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new prompt template."""
    template = PromptTemplate(
        name=data.get("name", "新模板"),
        category=data.get("category", "通用"),
        description=data.get("description", ""),
        content=data.get("content", ""),
        is_builtin=False,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return {"id": template.id}


@router.put("/{template_id}")
async def update_template(template_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update a prompt template."""
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    for key in ("name", "category", "description", "content"):
        if key in data:
            setattr(template, key, data[key])
    await db.commit()
    return {"id": template_id, "updated": True}


@router.delete("/{template_id}")
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a prompt template."""
    result = await db.execute(select(PromptTemplate).where(PromptTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(template)
    await db.commit()
    return {"deleted": True}
