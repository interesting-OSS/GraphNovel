"""Character API routes — CRUD + AI generation via graph + import/export."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.character import Character
from app.graphs.state import NovelState
from app.config import settings
from app.graphs.utils import get_gen_config
from app.logger import get_logger
import json

router = APIRouter(prefix="/characters", tags=["characters"])
logger = get_logger(__name__)


@router.get("/project/{project_id}")
async def list_characters(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all characters for a project."""
    result = await db.execute(
        select(Character).where(Character.project_id == project_id)
    )
    characters = result.scalars().all()
    return {
        "items": [{"id": c.id, "name": c.name, "gender": c.gender, "age": c.age,
                    "role_type": c.role_type, "personality": c.personality,
                    "power_level": c.power_level, "career_id": c.career_id,
                    "org_id": c.organization_id, "color": c.ui_color, "avatar_url": c.avatar_url,
                    "mental_state": c.mental_state, "motto": c.motto} for c in characters],
        "total": len(characters),
    }


@router.post("")
async def create_character(data: dict, db: AsyncSession = Depends(get_db)):
    """Create a new character."""
    character = Character(
        project_id=data.get("project_id", ""),
        name=data.get("name", "新角色"),
        gender=data.get("gender", "男"),
        age=data.get("age", 20),
        role_type=data.get("role_type", "supporting"),
        appearance=data.get("appearance", ""),
        personality=data.get("personality", ""),
        background=data.get("background", ""),
        goals=data.get("goals", ""),
        secrets=data.get("secrets", ""),
        mental_state=data.get("mental_state", "正常"),
        power_level=data.get("power_level", ""),
        career_id=data.get("career_id"),
        organization_id=data.get("org_id"),
        current_location=data.get("location", ""),
        motto=data.get("motto", ""),
        color=data.get("color", "#4ECDC4"),
        avatar_url=data.get("avatar_url"),
    )
    db.add(character)
    await db.commit()
    await db.refresh(character)
    return {"id": character.id}


@router.get("/{character_id}")
async def get_character(character_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single character with full details."""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    return {
        "id": character.id, "name": character.name, "gender": character.gender,
        "age": character.age, "role_type": character.role_type,
        "appearance": character.appearance, "personality": character.personality,
        "background": character.background, "goals": character.goals,
        "secrets": character.secrets, "mental_state": character.mental_state,
        "power_level": character.power_level, "career_id": character.career_id,
        "org_id": character.organization_id, "location": character.current_location,
        "motto": character.motto, "color": character.ui_color, "avatar_url": character.avatar_url,
    }


@router.put("/{character_id}")
async def update_character(character_id: str, data: dict, db: AsyncSession = Depends(get_db)):
    """Update a character."""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")

    updatable = ("name", "gender", "age", "role_type", "appearance", "personality",
                 "background", "goals", "secrets", "mental_state", "power_level",
                 "career_id", "organization_id", "current_location", "motto",
                 "ui_color", "avatar_url")
    for key in updatable:
        if key in data:
            setattr(character, key, data[key])
    await db.commit()
    return {"id": character_id, "updated": True}


@router.delete("/{character_id}")
async def delete_character(character_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a character."""
    result = await db.execute(select(Character).where(Character.id == character_id))
    character = result.scalar_one_or_none()
    if not character:
        raise HTTPException(status_code=404, detail="Character not found")
    await db.delete(character)
    await db.commit()
    return {"deleted": True}


@router.post("/generate")
async def generate_characters(data: dict):
    """Generate characters via graph's char_create subgraph nodes."""
    from app.graphs.subgraphs.char_create import (
        generate_protagonist, generate_supporting, generate_antagonist,
    )

    role_type = data.get("role_type", "supporting")
    state = NovelState(
        project_id=data.get("project_id", ""),
        title=data.get("title", ""),
        genre=data.get("genre", "玄幻"),
        world_setting=data.get("world_setting", {}),
        characters=data.get("existing_characters", []),
        generation_config=get_gen_config(data, temperature=0.8, max_tokens=16000),
    )

    try:
        if role_type == "protagonist":
            result = await generate_protagonist(state)
        elif role_type == "antagonist":
            result = await generate_antagonist(state)
        else:
            result = await generate_supporting(state)

        characters = result.get("characters", [])
        return {"status": "completed", "characters": characters}
    except Exception as e:
        logger.error("Character generation failed: %s", e)
        return {"status": "failed", "error": str(e)}


@router.post("/export")
async def export_characters(data: dict, db: AsyncSession = Depends(get_db)):
    """Export characters as JSON."""
    character_ids = data.get("character_ids", [])
    if not character_ids:
        return {"export_data": [], "count": 0}

    result = await db.execute(
        select(Character).where(Character.id.in_(character_ids))
    )
    characters = result.scalars().all()

    export_data = []
    for c in characters:
        export_data.append({
            "name": c.name, "gender": c.gender, "age": c.age,
            "role_type": c.role_type, "appearance": c.appearance,
            "personality": c.personality, "background": c.background,
            "goals": c.goals, "secrets": c.secrets,
            "mental_state": c.mental_state, "power_level": c.power_level,
            "career_id": c.career_id, "motto": c.motto, "color": c.color,
        })
    return {"export_data": export_data, "count": len(export_data)}


@router.post("/import")
async def import_characters(data: dict, db: AsyncSession = Depends(get_db)):
    """Import characters from JSON data."""
    project_id = data.get("project_id", "")
    import_data = data.get("import_data", [])

    imported = []
    for char_data in import_data:
        character = Character(
            project_id=project_id,
            name=char_data.get("name", "导入角色"),
            gender=char_data.get("gender", "男"),
            age=char_data.get("age", 20),
            role_type=char_data.get("role_type", "supporting"),
            appearance=char_data.get("appearance", ""),
            personality=char_data.get("personality", ""),
            background=char_data.get("background", ""),
            goals=char_data.get("goals", ""),
            secrets=char_data.get("secrets", ""),
            mental_state=char_data.get("mental_state", "正常"),
            power_level=char_data.get("power_level", ""),
            career_id=char_data.get("career_id"),
            motto=char_data.get("motto", ""),
            color=char_data.get("color", "#4ECDC4"),
        )
        db.add(character)
        imported.append(char_data.get("name", "导入角色"))

    await db.commit()
    return {"imported": imported, "count": len(imported)}
