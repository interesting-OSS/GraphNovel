"""Outline CRUD + AI generation API routes (via graph)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.outline import Outline
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.config import settings
from app.graphs.utils import get_gen_config
from app.logger import get_logger

router = APIRouter(prefix="/outlines", tags=["outlines"])
logger = get_logger(__name__)


@router.get("/project/{project_id}")
async def list_outlines(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all outlines for a project."""
    result = await db.execute(
        select(Outline).where(Outline.project_id == project_id).order_by(Outline.volume, Outline.chapter_index)
    )
    outlines = result.scalars().all()
    return {
        "items": [{"id": o.id, "volume": o.volume, "chapter_index": o.chapter_index,
                    "title": o.title, "summary": o.summary, "key_points": o.key_points,
                    "mode": o.mode, "expansion_strategy": o.expansion_strategy,
                    "target_words": o.target_words, "sort_order": o.sort_order} for o in outlines],
        "total": len(outlines),
    }


@router.post("")
async def create_outline(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new outline entry."""
    chapter_index_val = data.get("chapter_index", data.get("chapter_num", 1))
    outline = Outline(
        project_id=data.get("project_id", ""),
        volume=data.get("volume", 1),
        chapter_index=chapter_index_val,
        title=data.get("title", "新章节"),
        summary=data.get("summary", ""),
        key_points=data.get("key_points", ""),
        mode=data.get("mode", "one-to-one"),
        expansion_strategy=data.get("expansion_strategy", "balanced"),
        target_words=data.get("target_words", 3000),
        sort_order=data.get("sort_order", chapter_index_val),
        parent_id=data.get("parent_id"),
    )
    db.add(outline)
    await db.commit()
    await db.refresh(outline)
    return {"id": outline.id}


@router.put("/{outline_id}")
async def update_outline(outline_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update an outline entry."""
    result = await db.execute(select(Outline).where(Outline.id == outline_id))
    outline = result.scalar_one_or_none()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")

    for key in ("title", "summary", "key_points", "volume", "chapter_index",
                 "mode", "expansion_strategy", "target_words", "sort_order", "parent_id"):
        if key in data:
            setattr(outline, key, data[key])
        elif key == "chapter_index" and "chapter_num" in data:
            setattr(outline, "chapter_index", data["chapter_num"])
    await db.commit()
    return {"id": outline_id, "updated": True}


@router.delete("/{outline_id}")
async def delete_outline(outline_id: str, db: AsyncSession = Depends(get_db)):
    """Delete an outline entry."""
    result = await db.execute(select(Outline).where(Outline.id == outline_id))
    outline = result.scalar_one_or_none()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")
    await db.delete(outline)
    await db.commit()
    return {"deleted": True}


@router.post("/reorder")
async def reorder_outlines(data: dict, db: AsyncSession = Depends(get_db)):
    """Reorder outlines (batch update chapter_index, single query)."""
    items = data.get("items", [])
    if not items:
        return {"status": "no items"}
    # Batch fetch all outlines by IDs in one query
    ids = [item.get("id") for item in items if item.get("id")]
    result = await db.execute(select(Outline).where(Outline.id.in_(ids)))
    outline_map = {o.id: o for o in result.scalars().all()}
    for item in items:
        outline = outline_map.get(item.get("id"))
        if outline:
            outline.chapter_index = item.get("chapter_index", item.get("chapter_num", outline.chapter_index))
            outline.volume = item.get("volume", outline.volume)
    await db.commit()
    return {"status": "reordered"}


@router.post("/generate")
async def generate_outlines(data: dict):
    """Generate outlines via the graph's outline_plan_node."""
    from app.graphs.main_graph import outline_plan_node

    state = NovelState(
        project_id=data.get("project_id", ""),
        title=data.get("title", ""),
        genre=data.get("genre", "玄幻"),
        description=data.get("description", ""),
        target_words=data.get("target_words", 100000),
        outline_mode=data.get("outline_mode", "one-to-one"),
        world_setting=data.get("world_setting", {}),
        characters=data.get("characters", []),
        generation_config=get_gen_config(data),
    )

    try:
        result = await outline_plan_node(state)
        return {"status": "completed", "outlines": result.get("outlines", [])}
    except Exception as e:
        logger.error("Outline generation failed: %s", e)
        return {"status": "failed", "error": str(e)}


@router.post("/expand/{outline_id}")
async def expand_outline(outline_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Expand an outline node into more detailed sub-points."""
    result = await db.execute(select(Outline).where(Outline.id == outline_id))
    outline = result.scalar_one_or_none()
    if not outline:
        raise HTTPException(status_code=404, detail="Outline not found")

    ai = create_ai_service(
        provider=data.get("provider", "openai"),
        api_key=data.get("api_key"),
        model=data.get("model", settings.default_llm_model),
        temperature=0.7,
        max_tokens=8000,
    )

    prompt = f"""请将以下大纲要点扩展为更详细的场景规划：
章节标题：{outline.title}
摘要：{outline.summary}
要点：{outline.key_points}

以JSON格式输出：
```json
{{"scenes": [{{"name": "场景名", "description": "描述", "characters": ["角色"], "conflict": "冲突", "goal": "目标"}}], "expanded_summary": "扩展后的摘要", "expanded_key_points": "扩展后的要点"}}
```
只输出JSON。"""

    try:
        result = await ai.generate_json("你是一位小说大纲规划师。只输出JSON。", prompt)
        outcome = {"status": "expanded", "outline_id": outline_id, **result}
        return outcome
    except Exception as e:
        logger.error("Outline expansion failed: %s", e)
        return {"status": "failed", "error": str(e)}
