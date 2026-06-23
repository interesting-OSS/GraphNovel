"""Memory / Chapter Analysis API routes — vector search and analysis retrieval."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.memory import StoryMemory, PlotAnalysis
from app.memory.vector_store import VectorStore
from app.memory.memory_manager import MemoryManager
from app.logger import get_logger

router = APIRouter(prefix="/memories", tags=["memories"])
logger = get_logger(__name__)

_vector_store = None
_memory_manager = None


def _get_memory_manager() -> MemoryManager:
    global _memory_manager, _vector_store
    if _memory_manager is None:
        _vector_store = VectorStore()
        _memory_manager = MemoryManager(_vector_store)
    return _memory_manager


@router.get("/project/{project_id}")
async def list_memories(project_id: str, db: AsyncSession = Depends(get_db)):
    """List all plot memories and analyses for a project."""
    memories_result = await db.execute(
        select(StoryMemory).where(StoryMemory.project_id == project_id)
    )
    analyses_result = await db.execute(
        select(PlotAnalysis).where(PlotAnalysis.project_id == project_id)
    )
    memories = memories_result.scalars().all()
    analyses = analyses_result.scalars().all()

    return {
        "memories": [{"id": m.id, "chapter_index": m.chapter_index, "summary": m.summary,
                       "memory_layer": m.memory_layer, "type": m.memory_type} for m in memories],
        "analyses": [{"id": a.id, "chapter_index": a.chapter_index, "quality_score": a.quality_score,
                       "engagement_score": a.engagement_score, "coherence_score": a.coherence_score} for a in analyses],
        "total": len(memories) + len(analyses),
    }


@router.get("/project/{project_id}/search")
async def search_memories(project_id: str, q: str = "", layer: str = ""):
    """Semantic search through vector memories."""
    if not q:
        return {"results": []}

    try:
        mgr = _get_memory_manager()
        if layer:
            results = await mgr.retrieve_by_layer(project_id, q, layer, n_results=10)
        else:
            results = await mgr.retrieve_context(project_id, q, n_results=10)

        formatted = []
        if results and results.get("documents"):
            for i, doc_list in enumerate(results["documents"]):
                for j, doc in enumerate(doc_list):
                    # Get metadata at the same index
                    meta = {}
                    if results.get("metadatas") and i < len(results["metadatas"]):
                        if j < len(results["metadatas"][i]):
                            meta = results["metadatas"][i][j] or {}
                    formatted.append({
                        "content": (doc or "")[:500],
                        "metadata": meta,
                        "score": results.get("distances", [[1.0]])[i][j] if results.get("distances") else 1.0,
                    })
        return {"results": formatted[:10]}
    except Exception as e:
        logger.exception("Memory search failed for %s", project_id)
        return {"results": [], "error": str(e)}


@router.get("/project/{project_id}/analysis/{chapter_id}")
async def get_chapter_analysis(project_id: str, chapter_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed chapter analysis results."""
    result = await db.execute(
        select(PlotAnalysis).where(
            PlotAnalysis.project_id == project_id,
            PlotAnalysis.chapter_id == chapter_id,
        )
    )
    analysis = result.scalar_one_or_none()
    if not analysis:
        return {"analysis": {}, "message": "No analysis found for this chapter"}

    import json
    return {
        "analysis": {
            "id": analysis.id, "chapter_index": analysis.chapter_index,
            "plot_points": json.loads(analysis.plot_points) if analysis.plot_points else [],
            "conflict_info": json.loads(analysis.conflict_info) if analysis.conflict_info else {},
            "emotional_arc": json.loads(analysis.emotional_arc) if analysis.emotional_arc else {},
            "pacing_analysis": json.loads(analysis.pacing_analysis) if analysis.pacing_analysis else {},
            "quality_score": analysis.quality_score,
            "engagement_score": analysis.engagement_score,
            "coherence_score": analysis.coherence_score,
            "suggestions": json.loads(analysis.suggestions) if analysis.suggestions else [],
            "summary": analysis.summary,
            "report": analysis.report,
        }
    }


@router.delete("/project/{project_id}")
async def clear_memories(project_id: str):
    """Delete all memories for a project."""
    try:
        mgr = _get_memory_manager()
        await mgr.delete_project_memories(project_id)
        return {"deleted": True}
    except Exception as e:
        logger.exception("Failed to clear memories for %s", project_id)
        return {"deleted": False, "error": str(e)}
