"""Graph → DB sync utilities.

Graph nodes operate on NovelState (in-memory + checkpoint).
This module provides write-through functions so that graph outputs
are persisted to PostgreSQL tables as well.

All functions create their own DB session (no FastAPI dependency injection
available during graph execution), following the same pattern as
post_analysis_pipeline_node in chapter_analyze.py.
"""

import json
import uuid
import logging

from sqlalchemy import select
from app.database import async_session_factory
from app.models.project import Project
from app.models.character import Character
from app.models.outline import Outline
from app.models.chapter import Chapter
from app.models.relationship import Career, Organization

logger = logging.getLogger(__name__)


async def sync_project_init(project_id: str, title: str, description: str,
                            genre: str, narrative_perspective: str) -> None:
    """Persist project metadata after project_init_node completes."""
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if project:
                project.title = title or project.title
                project.description = description or project.description
                project.genre = genre or project.genre
                project.narrative_perspective = narrative_perspective or project.narrative_perspective
                await db.commit()
    except Exception:
        logger.exception("sync_project_init failed for %s", project_id)


async def sync_world_setting(project_id: str, world_setting: dict) -> None:
    """Persist world_setting to Project.world_setting (JSON string)."""
    if not world_setting:
        return
    try:
        async with async_session_factory() as db:
            result = await db.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()
            if project:
                project.world_setting = json.dumps(world_setting, ensure_ascii=False)
                await db.commit()
                logger.info("World setting synced for %s", project_id)
    except Exception:
        logger.exception("sync_world_setting failed for %s", project_id)


async def sync_outlines(project_id: str, outlines: list) -> None:
    """Persist outline list to outlines table (replace existing)."""
    if not outlines:
        return
    try:
        async with async_session_factory() as db:
            # Delete existing outlines for this project
            existing = await db.execute(
                select(Outline).where(Outline.project_id == project_id)
            )
            for o in existing.scalars().all():
                await db.delete(o)

            # Insert new outlines
            for i, ol in enumerate(outlines):
                outline = Outline(
                    project_id=project_id,
                    volume=ol.get("volume", 1),
                    chapter_index=ol.get("chapter_index", i + 1),
                    title=ol.get("title", f"第{i+1}章"),
                    summary=ol.get("summary", ""),
                    key_points=ol.get("key_points", ""),
                    mode=ol.get("mode", "one-to-one"),
                    expansion_strategy=ol.get("expansion_strategy", "balanced"),
                    target_words=ol.get("target_words", 3000),
                    sort_order=i,
                )
                db.add(outline)

            await db.commit()
            logger.info("Outlines synced for %s: %d entries", project_id, len(outlines))
    except Exception:
        logger.exception("sync_outlines failed for %s", project_id)


async def sync_careers(project_id: str, careers: list) -> None:
    """Persist career list to careers table (replace existing)."""
    if not careers:
        return
    try:
        async with async_session_factory() as db:
            existing = await db.execute(
                select(Career).where(Career.project_id == project_id)
            )
            for c in existing.scalars().all():
                await db.delete(c)

            for career_data in careers:
                career = Career(
                    project_id=project_id,
                    name=career_data.get("name", "未命名职业"),
                    career_type=career_data.get("type", career_data.get("career_type", "主要职业")),
                    description=career_data.get("description", ""),
                    levels=json.dumps(career_data.get("levels", []), ensure_ascii=False),
                )
                db.add(career)

            await db.commit()
            logger.info("Careers synced for %s: %d entries", project_id, len(careers))
    except Exception:
        logger.exception("sync_careers failed for %s", project_id)


async def sync_organizations(project_id: str, organizations: list) -> None:
    """Persist organization list to organizations table (replace existing)."""
    if not organizations:
        return
    try:
        async with async_session_factory() as db:
            existing = await db.execute(
                select(Organization).where(Organization.project_id == project_id)
            )
            for o in existing.scalars().all():
                await db.delete(o)

            for org_data in organizations:
                org = Organization(
                    project_id=project_id,
                    name=org_data.get("name", "未命名组织"),
                    org_type=org_data.get("type", org_data.get("org_type", "门派")),
                    goal=org_data.get("goal", ""),
                    description=org_data.get("description", ""),
                    alignment=org_data.get("alignment", "中立"),
                    hierarchy=json.dumps(org_data.get("hierarchy", []), ensure_ascii=False)
                    if org_data.get("hierarchy") else None,
                )
                db.add(org)

            await db.commit()
            logger.info("Organizations synced for %s: %d entries", project_id, len(organizations))
    except Exception:
        logger.exception("sync_organizations failed for %s", project_id)


async def sync_characters(project_id: str, characters: list) -> None:
    """Persist character list to characters table (upsert by name within project)."""
    if not characters:
        return
    try:
        async with async_session_factory() as db:
            # Get existing characters for this project
            existing_result = await db.execute(
                select(Character).where(Character.project_id == project_id)
            )
            existing_chars = {c.name: c for c in existing_result.scalars().all()}

            for char_data in characters:
                name = char_data.get("name", "")
                if not name:
                    continue

                if name in existing_chars:
                    # Update existing
                    ch = existing_chars[name]
                else:
                    # Create new
                    ch = Character(project_id=project_id, name=name)
                    db.add(ch)
                    existing_chars[name] = ch

                ch.gender = char_data.get("gender", ch.gender or "男")
                ch.age = char_data.get("age", ch.age)
                ch.role_type = char_data.get("role_type", ch.role_type or "supporting")
                ch.appearance = char_data.get("appearance", ch.appearance)
                ch.personality = char_data.get("personality", ch.personality)
                ch.background = char_data.get("background", ch.background)
                ch.goals = char_data.get("goals", ch.goals)
                ch.secrets = char_data.get("secrets", ch.secrets)
                ch.mental_state = char_data.get("mental_state", ch.mental_state)
                ch.power_level = char_data.get("power_level", ch.power_level)
                ch.current_location = char_data.get("location", ch.current_location)
                ch.motto = char_data.get("motto", ch.motto)
                ch.ui_color = char_data.get("color", ch.ui_color or "#4D8088")

            await db.commit()
            logger.info("Characters synced for %s: %d entries", project_id, len(characters))
    except Exception:
        logger.exception("sync_characters failed for %s", project_id)


async def sync_relationships(project_id: str, relationships: list) -> None:
    """Persist character relationships to character_relationships table (upsert by char pair)."""
    if not relationships:
        return
    try:
        async with async_session_factory() as db:
            for rel in relationships:
                char_a_id = rel.get("char_a_id", "")
                char_b_id = rel.get("char_b_id", "")
                if not char_a_id or not char_b_id:
                    continue
                # Check if relationship already exists
                existing = await db.execute(
                    select(CharacterRelationship).where(
                        CharacterRelationship.project_id == project_id,
                        CharacterRelationship.char_a_id == char_a_id,
                        CharacterRelationship.char_b_id == char_b_id,
                    )
                )
                existing_rel = existing.scalar_one_or_none()
                if existing_rel:
                    existing_rel.relation_type = rel.get("relation_type", existing_rel.relation_type)
                    existing_rel.description = rel.get("description", existing_rel.description)
                    existing_rel.intimacy = rel.get("intimacy", existing_rel.intimacy)
                    existing_rel.status = rel.get("status", existing_rel.status)
                else:
                    cr = CharacterRelationship(
                        project_id=project_id,
                        char_a_id=char_a_id,
                        char_b_id=char_b_id,
                        relation_type=rel.get("relation_type", "其他"),
                        description=rel.get("description", ""),
                        intimacy=rel.get("intimacy", 50.0),
                        status=rel.get("status", "正常"),
                        source=rel.get("source", "ai_generated"),
                    )
                    db.add(cr)
            await db.commit()
            logger.info("Relationships synced for %s: %d entries", project_id, len(relationships))
    except Exception:
        logger.exception("sync_relationships failed for %s", project_id)


async def sync_chapter(project_id: str, chapter_data: dict) -> str | None:
    """Persist a single chapter to the chapters table (upsert by chapter_index).

    Returns the chapter ID (new or existing).
    """
    if not chapter_data:
        return None
    try:
        async with async_session_factory() as db:
            chapter_index = chapter_data.get("chapter_index", 0)
            result = await db.execute(
                select(Chapter).where(
                    Chapter.project_id == project_id,
                    Chapter.chapter_index == chapter_index,
                )
            )
            chapter = result.scalar_one_or_none()

            if chapter:
                # Update existing
                chapter.title = chapter_data.get("title", chapter.title)
                chapter.content = chapter_data.get("content", chapter.content)
                chapter.word_count = chapter_data.get("word_count", len(chapter_data.get("content", "")))
                chapter.status = chapter_data.get("status", chapter.status)
            else:
                # Create new
                chapter = Chapter(
                    project_id=project_id,
                    chapter_index=chapter_index,
                    title=chapter_data.get("title", f"第{chapter_index}章"),
                    content=chapter_data.get("content", ""),
                    word_count=chapter_data.get("word_count", 0),
                    status=chapter_data.get("status", "draft"),
                )
                db.add(chapter)

            await db.commit()
            await db.refresh(chapter)
            logger.info("Chapter synced for %s: index=%d id=%s", project_id, chapter_index, chapter.id)
            return chapter.id
    except Exception:
        logger.exception("sync_chapter failed for %s chapter %d", project_id, chapter_data.get("chapter_index", 0))
        return None
