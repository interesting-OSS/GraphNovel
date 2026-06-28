"""Project CRUD API routes."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.project import Project
from app.logger import get_logger

router = APIRouter(prefix="/projects", tags=["projects"])
logger = get_logger(__name__)


@router.get("")
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
    result = await db.execute(
        select(Project).order_by(Project.updated_at.desc())
    )
    projects = result.scalars().all()
    return {
        "items": [{
            "id": p.id, "title": p.title, "description": p.description,
            "genre": p.genre, "status": p.status, "total_word_count": p.total_word_count,
            "narrative_perspective": p.narrative_perspective, "outline_mode": p.outline_mode,
            "cover_url": p.cover_url, "created_at": str(p.created_at),
            "updated_at": str(p.updated_at),
        } for p in projects],
        "total": len(projects),
    }


@router.post("")
async def create_project(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new project."""
    project = Project(
        title=data.get("title", "未命名项目"),
        description=data.get("description"),
        genre=data.get("genre", "玄幻"),
        target_words=data.get("target_words", 100000),
        narrative_perspective=data.get("narrative_perspective", "第三人称"),
        outline_mode=data.get("outline_mode", "one-to-one"),
        status=data.get("status", "planning"),
        world_setting=json.dumps(data.get("world_setting", {}), ensure_ascii=False) if data.get("world_setting") else None,
        writing_style_id=data.get("writing_style_id"),
        generation_config=json.dumps(data.get("generation_config", {}), ensure_ascii=False) if data.get("generation_config") else None,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return {"id": project.id, "message": "Project created", "title": project.title}


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single project with full details."""
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

    generation_config = {}
    if project.generation_config:
        try:
            generation_config = json.loads(project.generation_config)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "id": project.id, "title": project.title, "description": project.description,
        "genre": project.genre, "target_words": project.target_words,
        "narrative_perspective": project.narrative_perspective,
        "status": project.status, "total_word_count": project.total_word_count,
        "outline_mode": project.outline_mode, "world_setting": world_setting,
        "cover_prompt": project.cover_prompt, "cover_url": project.cover_url,
        "writing_style_id": project.writing_style_id,
        "active_skill": project.active_skill,
        "generation_config": generation_config,
        "created_at": str(project.created_at), "updated_at": str(project.updated_at),
    }


@router.put("/{project_id}")
async def update_project(project_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    updatable = ("title", "description", "genre", "target_words", "narrative_perspective",
                 "status", "total_word_count", "outline_mode", "cover_prompt", "cover_url",
                 "writing_style_id", "active_skill")
    for key in updatable:
        if key in data:
            setattr(project, key, data[key])

    if "world_setting" in data:
        project.world_setting = json.dumps(data["world_setting"], ensure_ascii=False)
    if "generation_config" in data:
        project.generation_config = json.dumps(data["generation_config"], ensure_ascii=False)

    await db.commit()
    return {"id": project_id, "updated": True}


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project and all associated data (cascading)."""
    import logging
    _log = logging.getLogger(__name__)

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Bulk delete child rows (single DELETE per model, avoids N+1)
    from sqlalchemy import delete as sql_delete
    from app.models.chapter import Chapter
    from app.models.outline import Outline
    from app.models.character import Character
    from app.models.relationship import Career, Organization, OrganizationMember, CharacterRelationship
    from app.models.foreshadow import Foreshadow
    from app.models.generation import GenerationHistory
    from app.models.memory import PlotAnalysis
    from app.models.background_task import BackgroundTask

    # Models with project_id: simple bulk delete
    for model in [Foreshadow, GenerationHistory, PlotAnalysis, Chapter, Outline,
                  Character, Career, Organization, BackgroundTask]:
        try:
            await db.execute(sql_delete(model).where(model.project_id == project_id))
        except Exception as e:
            _log.warning("Failed to cascade delete %s: %s", model.__name__, e)

    # Models without project_id: delete via FK (OrganizationMember, CharacterRelationship)
    for model in [CharacterRelationship]:
        try:
            await db.execute(sql_delete(model).where(model.project_id == project_id))
        except Exception as e:
            _log.warning("Failed to cascade delete %s: %s", model.__name__, e)
    # OrganizationMember: deleted via organization_id join or cascade from above

    await db.flush()
    await db.delete(project)
    await db.commit()
    _log.info("Project %s deleted successfully", project_id)
    return {"deleted": True}


@router.post("/{project_id}/export")
async def export_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Export a full project as JSON for backup or sharing."""
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

    export_data = {
        "version": "1.0",
        "project": {
            "title": project.title, "description": project.description,
            "genre": project.genre, "target_words": project.target_words,
            "narrative_perspective": project.narrative_perspective,
            "world_setting": world_setting,
            "outline_mode": project.outline_mode,
        },
    }
    return {"export_data": export_data}


@router.post("/import")
async def import_project(data: dict, db: AsyncSession = Depends(get_db)):
    """Import a project from JSON export data."""
    export_data = data.get("export_data", {})
    project_data = export_data.get("project", {})

    project = Project(
        title=project_data.get("title", "导入项目"),
        description=project_data.get("description"),
        genre=project_data.get("genre", "玄幻"),
        target_words=project_data.get("target_words", 100000),
        narrative_perspective=project_data.get("narrative_perspective", "第三人称"),
        outline_mode=project_data.get("outline_mode", "one-to-one"),
        status="planning",
        world_setting=json.dumps(project_data.get("world_setting", {}), ensure_ascii=False),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return {"id": project.id, "title": project.title, "message": "Project imported"}


@router.post("/{project_id}/export-subgraph")
async def export_project_subgraph(project_id: str, data: dict = {}):
    """Export full project data via LangGraph ExportSubGraph.

    Returns structured JSON with characters, chapters, outlines, world_setting, etc.
    Supports export modes: full (default), characters, organizations.
    """
    from app.graphs.subgraphs.export_data import create_export_subgraph
    subgraph = create_export_subgraph()
    state = {
        "project_id": project_id,
        "_export_mode": data.get("mode", "full"),
    }
    result = await subgraph.ainvoke(state)
    return {"export_data": result.get("_export_data", {}),
            "export_json": result.get("_export_json", "")}


@router.post("/import-subgraph")
async def import_project_subgraph(data: dict):
    """Import project data via LangGraph ImportSubGraph.

    Accepts full/characters/organizations import data and merges into state.
    """
    from app.graphs.subgraphs.import_data import create_import_subgraph
    subgraph = create_import_subgraph()
    state = {
        "_import_mode": data.get("mode", "full"),
        "_import_data": data.get("import_data", {}),
        "characters": [],
        "relationships": [],
        "organizations": [],
        "careers": [],
        "chapters": [],
    }
    result = await subgraph.ainvoke(state)
    return {"imported_characters": len(result.get("characters", [])),
            "imported_organizations": len(result.get("organizations", [])),
            "message": "Import subgraph completed"}
