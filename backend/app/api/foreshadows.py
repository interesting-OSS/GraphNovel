"""Foreshadow Management API — full lifecycle: plant, resolve, abandon, sync, stats, timeline."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func as sqlfunc
from app.database import get_db
from app.models.foreshadow import Foreshadow
from app.graphs.subgraphs.foreshadow import create_foreshadow_subgraph
from app.logger import get_logger

router = APIRouter(prefix="/foreshadows", tags=["foreshadows"])
logger = get_logger(__name__)


# ── CRUD ──


@router.get("/project/{project_id}")
async def list_foreshadows(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all foreshadows for a project, sorted by set chapter."""
    result = await db.execute(
        select(Foreshadow)
        .where(Foreshadow.project_id == project_id)
        .order_by(Foreshadow.set_chapter_id.asc(), Foreshadow.target_chapter_index.asc())
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": f.id,
                "description": f.description,
                "status": f.status,
                "category": f.category,
                "set_chapter_id": f.set_chapter_id,
                "target_chapter_index": f.target_chapter_index,
                "resolved_chapter_id": f.resolved_chapter_id,
                "remind_deadline": f.remind_deadline,
                "importance": f.importance,
                "created_at": str(f.created_at),
                "updated_at": str(f.updated_at),
            }
            for f in items
        ],
        "total": len(items),
    }


@router.post("")
async def create_foreshadow(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new foreshadow entry."""
    foreshadow = Foreshadow(
        project_id=data.get("project_id", ""),
        description=data.get("description", ""),
        category=data.get("category", "情节伏笔"),
        status=data.get("status", "pending"),
        set_chapter_id=data.get("set_chapter_id"),
        target_chapter_index=data.get("target_chapter_index"),
        remind_deadline=data.get("remind_deadline"),
        importance=data.get("importance", 5.0),
    )
    db.add(foreshadow)
    await db.commit()
    await db.refresh(foreshadow)
    return {"id": foreshadow.id}


@router.put("/{foreshadow_id}")
async def update_foreshadow(foreshadow_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update a foreshadow entry."""
    result = await db.execute(select(Foreshadow).where(Foreshadow.id == foreshadow_id))
    foreshadow = result.scalar_one_or_none()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="Foreshadow not found")

    updatable = ("description", "category", "status", "set_chapter_id",
                 "target_chapter_index", "remind_deadline", "importance")
    for key in updatable:
        if key in data:
            setattr(foreshadow, key, data[key])
    await db.commit()
    return {"id": foreshadow_id, "updated": True}


@router.delete("/{foreshadow_id}")
async def delete_foreshadow(foreshadow_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a foreshadow."""
    result = await db.execute(select(Foreshadow).where(Foreshadow.id == foreshadow_id))
    foreshadow = result.scalar_one_or_none()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="Foreshadow not found")
    await db.delete(foreshadow)
    await db.commit()
    return {"deleted": True}


# ── Lifecycle operations ──


@router.post("/{foreshadow_id}/plant")
async def plant_foreshadow(foreshadow_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Plant (set) a foreshadow — mark it as active with chapter context."""
    result = await db.execute(select(Foreshadow).where(Foreshadow.id == foreshadow_id))
    foreshadow = result.scalar_one_or_none()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="Foreshadow not found")

    foreshadow.status = "set"
    if data.get("set_chapter_id"):
        foreshadow.set_chapter_id = data["set_chapter_id"]
    if data.get("target_chapter_index"):
        foreshadow.target_chapter_index = data["target_chapter_index"]
    if data.get("remind_deadline"):
        foreshadow.remind_deadline = data["remind_deadline"]
    await db.commit()
    return {"id": foreshadow_id, "status": "set"}


@router.post("/{foreshadow_id}/resolve")
async def resolve_foreshadow(foreshadow_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Resolve a foreshadow — mark it as completed."""
    result = await db.execute(select(Foreshadow).where(Foreshadow.id == foreshadow_id))
    foreshadow = result.scalar_one_or_none()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="Foreshadow not found")

    foreshadow.status = "resolved"
    if data.get("resolved_chapter_id"):
        foreshadow.resolved_chapter_id = data["resolved_chapter_id"]
    await db.commit()
    return {"id": foreshadow_id, "status": "resolved"}


@router.post("/{foreshadow_id}/abandon")
async def abandon_foreshadow(foreshadow_id: str, db: AsyncSession = Depends(get_db)):
    """Abandon a foreshadow — this plot thread won't be used."""
    result = await db.execute(select(Foreshadow).where(Foreshadow.id == foreshadow_id))
    foreshadow = result.scalar_one_or_none()
    if not foreshadow:
        raise HTTPException(status_code=404, detail="Foreshadow not found")

    foreshadow.status = "abandoned"
    await db.commit()
    return {"id": foreshadow_id, "status": "abandoned"}


# ── Batch / Analysis operations ──


@router.post("/sync-from-analysis")
async def sync_from_analysis(data: dict, db: AsyncSession = Depends(get_db)):
    """Sync foreshadow status from chapter analysis via LangGraph ForeshadowSubGraph.

    Accepts the current NovelState-like dict and runs the foreshadow subgraph
    to auto-classify, check deadlines, and update statuses.
    """
    project_id = data.get("project_id", "")
    if not project_id:
        return {"synced": [], "message": "project_id required"}

    try:
        # Build a minimal state for the subgraph
        state = {
            "project_id": project_id,
            "current_chapter_index": data.get("current_chapter_index", 0),
            "foreshadows": data.get("foreshadows", []),
            "chapter_analyses": data.get("chapter_analyses", []),
        }
        subgraph = create_foreshadow_subgraph()
        config_ctx = {"configurable": {"thread_id": f"foreshadow_sync_{project_id}"}}
        result = await subgraph.ainvoke(state, config_ctx)

        synced = result.get("foreshadows", [])
        stats = result.get("_foreshadow_stats", {})
        warnings = result.get("_foreshadow_warnings", [])

        return {
            "synced": synced,
            "statistics": stats,
            "warnings": warnings,
            "message": f"Synced {len(synced)} foreshadows",
        }
    except Exception as e:
        logger.exception("Foreshadow sync failed for %s", project_id)
        return {"synced": [], "error": str(e)}


@router.get("/project/{project_id}/statistics")
async def get_statistics(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get aggregated foreshadow statistics: by status, category, resolution rate."""
    result = await db.execute(
        select(Foreshadow).where(Foreshadow.project_id == project_id)
    )
    foreshadows = result.scalars().all()

    if not foreshadows:
        return {"statistics": {"total": 0, "by_status": {}, "by_category": {}, "resolution_rate": 0.0}}

    by_status = {"pending": 0, "set": 0, "resolved": 0, "abandoned": 0}
    by_category = {}
    for f in foreshadows:
        by_status[f.status] = by_status.get(f.status, 0) + 1
        cat = f.category or "未分类"
        by_category[cat] = by_category.get(cat, 0) + 1

    total = len(foreshadows)
    resolved = by_status.get("resolved", 0)

    # Check deadlines
    warnings = []
    for f in foreshadows:
        if f.status == "set" and f.remind_deadline:
            warnings.append({
                "id": f.id,
                "description": f.description[:100],
                "category": f.category,
                "deadline": f.remind_deadline,
            })

    return {
        "statistics": {
            "total": total,
            "by_status": by_status,
            "by_category": by_category,
            "resolution_rate": round((resolved / total) * 100, 1),
            "warnings": warnings,
        }
    }


@router.get("/project/{project_id}/timeline")
async def get_timeline(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get foreshadow timeline — all entries sorted by chapter for visualization."""
    result = await db.execute(
        select(Foreshadow)
        .where(Foreshadow.project_id == project_id)
        .order_by(Foreshadow.target_chapter_index.asc(), Foreshadow.created_at.asc())
    )
    foreshadows = result.scalars().all()

    timeline = []
    for f in foreshadows:
        timeline.append({
            "id": f.id,
            "description": f.description[:150],
            "status": f.status,
            "category": f.category,
            "set_chapter_id": f.set_chapter_id,
            "target_chapter": f.target_chapter_index,
            "resolved_chapter_id": f.resolved_chapter_id,
            "importance": f.importance,
        })

    return {"timeline": timeline, "total": len(timeline)}
