"""Post-Analysis Pipeline — automatic state updates after chapter analysis.

Each step runs independently with its own try/catch, so one failure
never blocks subsequent steps. This is the automatic closed loop that
MuMuAINovel has and GraphNovel is now gaining:

  PlotAnalyzer result
    → update_character_states   (mental state + arc tracking)
    → update_career_progress    (career level progression detection)
    → auto_manage_foreshadows   (plant new / resolve triggered)
    → dual_write_memory          (SQL StoryMemory + ChromaDB vector)
    → update_relationships      (intimacy + status changes)
"""
import json
import logging
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.character import Character
from app.models.relationship import CharacterRelationship
from app.models.memory import StoryMemory, PlotAnalysis
from app.models.foreshadow import Foreshadow

logger = logging.getLogger(__name__)


class AnalysisPipeline:
    """Runs automatic post-analysis state mutations.

    Each public method is a standalone step — failures are logged but never re-raised.
    """

    def __init__(self, memory_manager=None):
        self._memory_manager = memory_manager

    async def run_full_pipeline(
        self,
        project_id: str,
        chapter_id: str,
        chapter_index: int,
        analysis_data: dict,
        db: AsyncSession,
    ) -> dict:
        """Execute all post-analysis steps for a completed chapter analysis.

        Args:
            project_id: Project UUID.
            chapter_id: Chapter UUID.
            chapter_index: Chapter number.
            analysis_data: The analysis result from chapter_analyze subgraph.
            db: Async database session.

        Returns:
            dict with per-step status (ok/error) for observability.
        """
        results = {}

        # Step 1: Update character states (mental, arc tracking)
        results["character_states"] = await _step(
            "character_states",
            self._update_character_states(project_id, analysis_data, db),
        )

        # Step 2: Update career progress
        results["career_progress"] = await _step(
            "career_progress",
            self._update_career_progress(project_id, chapter_index, analysis_data, db),
        )

        # Step 3: Auto-manage foreshadows
        results["foreshadow_management"] = await _step(
            "foreshadow_management",
            self._auto_manage_foreshadows(project_id, chapter_id, chapter_index, analysis_data, db),
        )

        # Step 4: Dual-write memory (SQL + ChromaDB)
        results["memory_sync"] = await _step(
            "memory_sync",
            self._dual_write_memory(project_id, chapter_id, chapter_index, analysis_data, db),
        )

        # Step 5: Update character relationships
        results["relationship_updates"] = await _step(
            "relationship_updates",
            self._update_relationships(project_id, chapter_index, analysis_data, db),
        )

        return results

    # ── Step implementations ─────────────────────────────────────────────

    async def _update_character_states(
        self, project_id: str, analysis_data: dict, db: AsyncSession,
    ):
        """Extract character arc changes from analysis and update mental_state."""
        # chapter_analyze.py stores under "character_changes", also check "character_arcs"
        character_arcs = analysis_data.get("character_changes") or analysis_data.get("character_arcs", [])
        if not character_arcs:
            # Try to parse from JSON string if stored that way
            raw = analysis_data.get("_character_changes_raw") or analysis_data.get("_character_arcs_raw", "")
            if raw:
                try:
                    character_arcs = json.loads(raw) if isinstance(raw, str) else raw
                except (json.JSONDecodeError, TypeError):
                    pass

        updated = 0
        for arc in (character_arcs or []):
            char_name = arc.get("character", arc.get("name", ""))
            new_state = arc.get("mental_state", arc.get("state", ""))
            if not char_name or not new_state:
                continue

            # Match by name (case-insensitive)
            result = await db.execute(
                select(Character).where(
                    Character.project_id == project_id,
                    Character.name.ilike(f"%{char_name}%"),
                )
            )
            chars = result.scalars().all()
            if len(chars) > 1:
                logger.warning("Fuzzy name '%s' matched %d characters: %s",
                             char_name, len(chars), [c.name for c in chars])
            for char in chars:
                char.mental_state = new_state
                char.updated_at = datetime.now()
                updated += 1
                logger.info("Character %s mental_state → %s", char.name, new_state)

        if updated:
            await db.commit()
        return {"characters_updated": updated}

    async def _update_career_progress(
        self, project_id: str, chapter_index: int, analysis_data: dict, db: AsyncSession,
    ):
        """Detect career progression from analysis hints and update character levels."""
        character_arcs = (analysis_data.get("character_changes") or analysis_data.get("character_arcs", []))
        if not character_arcs:
            raw = analysis_data.get("_character_changes_raw") or analysis_data.get("_character_arcs_raw", "")
            if raw:
                try:
                    character_arcs = json.loads(raw) if isinstance(raw, str) else raw
                except (json.JSONDecodeError, TypeError):
                    pass

        updated = 0
        for arc in (character_arcs or []):
            char_name = arc.get("character", arc.get("name", ""))
            career_event = arc.get("career_event", arc.get("progression", ""))
            new_power = arc.get("power_level", "")

            if not char_name or (not career_event and not new_power):
                continue

            result = await db.execute(
                select(Character).where(
                    Character.project_id == project_id,
                    Character.name.ilike(f"%{char_name}%"),
                )
            )
            chars = result.scalars().all()
            if len(chars) > 1:
                logger.warning("Fuzzy career name '%s' matched %d characters: %s",
                             char_name, len(chars), [c.name for c in chars])
            for char in chars:
                if career_event:
                    char.goals = (char.goals or "") + f"\n[第{chapter_index}章] {career_event}"
                if new_power:
                    char.power_level = new_power
                char.updated_at = datetime.now()
                updated += 1
                logger.info("Career update for %s: power=%s event=%s", char.name, new_power, career_event)

        if updated:
            await db.commit()
        return {"career_updates": updated}

    async def _auto_manage_foreshadows(
        self, project_id: str, chapter_id: str, chapter_index: int,
        analysis_data: dict, db: AsyncSession,
    ):
        """Auto-plant new foreshadows detected in analysis, and resolve those that were paid off."""
        planted = 0
        resolved = 0

        # Extract new foreshadows from analysis
        new_foreshadows = analysis_data.get("foreshadows", [])
        raw = analysis_data.get("_foreshadows_raw", "")
        if raw and not new_foreshadows:
            try:
                new_foreshadows = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                pass

        # Plant new ones (flush first so they get IDs before we resolve)
        new_foreshadow_ids = set()
        for fs in (new_foreshadows or []):
            if not isinstance(fs, dict):
                continue
            try:
                foreshadow = Foreshadow(
                    project_id=project_id,
                    description=fs.get("description", ""),
                    status="set",
                    category=fs.get("category", "情节伏笔"),
                    set_chapter_id=chapter_id,
                    target_chapter_index=fs.get("target_chapter_index"),
                    importance=fs.get("importance", 0.5),
                )
                db.add(foreshadow)
                await db.flush()  # Assign ID without committing
                new_foreshadow_ids.add(foreshadow.id)
                planted += 1
            except Exception as e:
                logger.warning("Failed to plant foreshadow: %s", e)

        # Resolve foreshadows whose target is this chapter (skip newly planted)
        due_result = await db.execute(
            select(Foreshadow).where(
                Foreshadow.project_id == project_id,
                Foreshadow.status == "set",
                Foreshadow.target_chapter_index <= chapter_index,
            )
        )
        for fs in due_result.scalars().all():
            if fs.id in new_foreshadow_ids:
                continue  # Don't resolve foreshadows planted in this same step
            fs.status = "resolved"
            fs.resolved_chapter_id = chapter_id
            fs.updated_at = datetime.now()
            resolved += 1
            logger.info("Foreshadow resolved: %s (ch%d)", fs.description[:50], chapter_index)

        if planted or resolved:
            await db.commit()

        return {"foreshadows_planted": planted, "foreshadows_resolved": resolved}

    async def _dual_write_memory(
        self, project_id: str, chapter_id: str, chapter_index: int,
        analysis_data: dict, db: AsyncSession,
    ):
        """Write memory to both SQL (StoryMemory) and ChromaDB (via MemoryManager)."""
        sql_count = 0
        vector_count = 0

        # 1. SQL: Save PlotAnalysis record
        try:
            analysis = PlotAnalysis(
                project_id=project_id,
                chapter_id=chapter_id,
                plot_points=json.dumps(analysis_data.get("plot_points", []), ensure_ascii=False),
                conflict_info=json.dumps(analysis_data.get("conflict_info", {}), ensure_ascii=False),
                emotional_arc=json.dumps(analysis_data.get("emotional_arc", {}), ensure_ascii=False),
                character_arcs=json.dumps((analysis_data.get("character_changes") or analysis_data.get("character_arcs", [])), ensure_ascii=False),
                pacing_score=analysis_data.get("pacing_score"),
                engagement_score=analysis_data.get("engagement_score"),
                coherence_score=analysis_data.get("coherence_score"),
                quality_score=analysis_data.get("quality_score"),
                suggestions=json.dumps(analysis_data.get("suggestions", []), ensure_ascii=False),
                report=analysis_data.get("report", ""),
                dialogue_ratio=analysis_data.get("dialogue_ratio"),
                description_ratio=analysis_data.get("description_ratio"),
                narrative_ratio=analysis_data.get("narrative_ratio"),
            )
            db.add(analysis)
            await db.commit()
            sql_count += 1
        except Exception as e:
            logger.warning("Failed to save PlotAnalysis: %s", e)

        # 2. SQL: Save StoryMemory records for extracted plot points
        plot_points = analysis_data.get("plot_points", [])
        for point in (plot_points or []):
            try:
                memory = StoryMemory(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    content=point.get("description", str(point)[:500]),
                    summary=point.get("summary", ""),
                    memory_type="plot",
                    importance=point.get("importance", 0.5),
                    tags=json.dumps(point.get("tags", []), ensure_ascii=False),
                )
                db.add(memory)
                sql_count += 1
            except Exception as e:
                logger.warning("Failed to save StoryMemory: %s", e)

        if sql_count > 0:
            await db.commit()

        # 3. ChromaDB: Vectorize key content via MemoryManager
        if self._memory_manager:
            try:
                plot_descriptions = []
                for point in (plot_points or []):
                    desc = point.get("description", "") if isinstance(point, dict) else str(point)
                    if desc:
                        plot_descriptions.append({"description": desc, "importance": point.get("importance", 0.5) if isinstance(point, dict) else 0.5})

                character_changes = (analysis_data.get("character_changes") or analysis_data.get("character_arcs", []))
                extracted_foreshadows = analysis_data.get("foreshadows", [])

                embedding_ids = await self._memory_manager.add_chapter_memory(
                    project_id=project_id,
                    chapter_id=chapter_id,
                    chapter_index=chapter_index,
                    content="",  # Content already saved separately
                    summary=analysis_data.get("report", "")[:1000],
                    plot_points=plot_descriptions,
                    character_changes=character_changes if isinstance(character_changes, list) else [],
                    foreshadows=extracted_foreshadows if isinstance(extracted_foreshadows, list) else [],
                )
                vector_count = len(embedding_ids)
            except Exception as e:
                logger.warning("Failed to write vector memory: %s", e)

        return {"sql_records": sql_count, "vector_embeddings": vector_count}

    async def _update_relationships(
        self, project_id: str, chapter_index: int, analysis_data: dict, db: AsyncSession,
    ):
        """Update character relationships based on analysis events."""
        conflict_info = analysis_data.get("conflict_info", {})
        character_arcs = (analysis_data.get("character_changes") or analysis_data.get("character_arcs", []))

        # Extract interacted character pairs from conflict info
        participants = conflict_info.get("participants", conflict_info.get("characters", []))
        if not participants:
            return {"relationships_updated": 0}

        updated = 0
        for i, char_a_name in enumerate(participants):
            for char_b_name in participants[i + 1:]:
                # Find both characters
                result_a = await db.execute(
                    select(Character).where(
                        Character.project_id == project_id,
                        Character.name.ilike(f"%{char_a_name}%"),
                    )
                )
                result_b = await db.execute(
                    select(Character).where(
                        Character.project_id == project_id,
                        Character.name.ilike(f"%{char_b_name}%"),
                    )
                )
                chars_a = result_a.scalars().all()
                chars_b = result_b.scalars().all()

                for ca in chars_a:
                    for cb in chars_b:
                        if ca.id == cb.id:
                            continue
                        # Find or update existing relationship
                        rel_result = await db.execute(
                            select(CharacterRelationship).where(
                                CharacterRelationship.project_id == project_id,
                                (
                                    (CharacterRelationship.char_a_id == ca.id) &
                                    (CharacterRelationship.char_b_id == cb.id)
                                ) | (
                                    (CharacterRelationship.char_a_id == cb.id) &
                                    (CharacterRelationship.char_b_id == ca.id)
                                ),
                            )
                        )
                        rel = rel_result.scalar_one_or_none()
                        if rel:
                            rel.intimacy = min(100, (rel.intimacy or 50) + 2)  # Slight intimacy bump
                            rel.updated_at = datetime.now()
                        else:
                            # Create a new relationship
                            rel = CharacterRelationship(
                                project_id=project_id,
                                char_a_id=ca.id,
                                char_b_id=cb.id,
                                relation_type="互动",
                                description=f"第{chapter_index}章首次互动",
                                intimacy=20,
                                source="ai_generated",
                            )
                            db.add(rel)
                        updated += 1

        if updated:
            await db.commit()
        return {"relationships_updated": updated}


# ── Helpers ──────────────────────────────────────────────────────────────


    def set_memory_manager(self, memory_manager):
        """Wire in the MemoryManager for ChromaDB vector writes."""
        self._memory_manager = memory_manager


async def _step(name: str, coro):
    """Execute a pipeline step, catching and logging errors without stopping."""
    try:
        return {"status": "ok", **(await coro)}
    except Exception as e:
        logger.exception("Pipeline step '%s' failed: %s", name, e)
        return {"status": "error", "error": str(e)}


# Singleton — initialized with MemoryManager in app startup
analysis_pipeline = AnalysisPipeline()
