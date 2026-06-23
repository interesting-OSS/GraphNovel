"""Writing Style API routes — CRUD + built-in presets."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.writing_style import WritingStyle
from app.logger import get_logger

router = APIRouter(prefix="/writing-styles", tags=["writing_styles"])
logger = get_logger(__name__)

BUILTIN_PRESETS = [
    {"id": "preset_ancient", "name": "古风", "description": "古典文风，适合仙侠、武侠类",
     "template": "采用古典白话风格，使用古雅的词汇和句式，注重意境营造和留白。"},
    {"id": "preset_light", "name": "轻小说", "description": "轻松明快的轻小说风格",
     "template": "使用轻松活泼的语气，多用短句和对话，节奏明快，注重角色个性表达。"},
    {"id": "preset_serious", "name": "严肃文学", "description": "严谨的文学性写作风格",
     "template": "采用严谨的文学语言，注重心理描写和环境渲染，句式丰富多变，追求文学深度。"},
    {"id": "preset_webnovel", "name": "网文风格", "description": "爽快流畅的网络小说风格",
     "template": "使用通俗流畅的语言，节奏快速，冲突密集，注重阅读爽感和代入感。"},
    {"id": "preset_dark", "name": "暗黑风格", "description": "压抑深沉的暗黑文风",
     "template": "使用深沉压抑的基调，注重阴暗面描写，节奏缓慢凝重，营造绝望或紧张氛围。"},
]


@router.get("")
async def list_styles(db: AsyncSession = Depends(get_db)):
    """List all custom writing styles from database."""
    result = await db.execute(select(WritingStyle))
    styles = result.scalars().all()
    return {
        "items": [{
            "id": s.id, "name": s.name, "description": s.description,
            "template": s.template, "is_builtin": s.is_builtin,
        } for s in styles],
        "total": len(styles),
    }


@router.get("/presets")
async def list_presets():
    """List built-in writing style presets."""
    return {"items": BUILTIN_PRESETS}


@router.post("")
async def create_style(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a custom writing style."""
    style = WritingStyle(
        project_id=data.get("project_id"),
        name=data.get("name", "新风格"),
        description=data.get("description", ""),
        template=data.get("template", ""),
        is_builtin=False,
    )
    db.add(style)
    await db.commit()
    await db.refresh(style)
    return {"id": style.id}


@router.put("/{style_id}")
async def update_style(style_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update a writing style."""
    result = await db.execute(select(WritingStyle).where(WritingStyle.id == style_id))
    style = result.scalar_one_or_none()
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")
    for key in ("name", "description", "template"):
        if key in data:
            setattr(style, key, data[key])
    await db.commit()
    return {"id": style_id, "updated": True}


@router.delete("/{style_id}")
async def delete_style(style_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a writing style."""
    result = await db.execute(select(WritingStyle).where(WritingStyle.id == style_id))
    style = result.scalar_one_or_none()
    if not style:
        raise HTTPException(status_code=404, detail="Style not found")
    await db.delete(style)
    await db.commit()
    return {"deleted": True}


@router.post("/initialize-defaults")
async def initialize_defaults(db: AsyncSession = Depends(get_db)):
    """Initialize built-in writing style presets into the database."""
    existing = await db.execute(select(WritingStyle).where(WritingStyle.is_builtin == True))
    if existing.scalars().first():
        return {"status": "already_initialized"}

    for preset in BUILTIN_PRESETS:
        style = WritingStyle(
            name=preset["name"],
            description=preset["description"],
            template=preset["template"],
            is_builtin=True,
        )
        db.add(style)
    await db.commit()
    return {"status": "initialized", "count": len(BUILTIN_PRESETS)}
