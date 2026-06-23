"""ForeshadowSubGraph — foreshadow lifecycle management with AI."""
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)


def _get_ai_service(state: NovelState, **overrides):
    config = state.get("generation_config", {})
    return create_ai_service(
        provider=overrides.pop("provider", config.get("provider", "openai")),
        api_key=overrides.pop("api_key", config.get("api_key", None)),
        base_url=overrides.pop("base_url", config.get("base_url", None)),
        model=overrides.pop("model", config.get("model", settings.default_ai_model)),
        temperature=overrides.pop("temperature", config.get("temperature", 0.3)),
        max_tokens=overrides.pop("max_tokens", config.get("max_tokens", 8000)),
        **overrides,
    )


async def sync_from_analysis(state: NovelState) -> dict:
    """Sync foreshadow status from chapter analysis results."""
    chapter_analyses = state.get("chapter_analyses", [])
    foreshadows = state.get("foreshadows", [])

    # Track which foreshadows were resolved in recent chapters
    for analysis in chapter_analyses:
        for hook in analysis.get("hooks", []):
            desc = hook.get("description", "")
            for f in foreshadows:
                if desc and desc[:30] in f.get("description", ""):
                    f["status"] = "resolved"

    return {"foreshadows": foreshadows, "current_phase": "foreshadows_synced"}


async def classify_foreshadow(state: NovelState) -> dict:
    """Classify foreshadows by category using AI."""
    ai = _get_ai_service(state)
    foreshadows = state.get("foreshadows", [])
    if not foreshadows:
        return {"current_phase": "foreshadows_classified"}

    unclassified = [f for f in foreshadows if not f.get("category") or f.get("category") == "未分类"]
    if not unclassified:
        return {"current_phase": "foreshadows_classified"}

    fs_text = "\n".join(f"- ID:{f.get('id', '')} 描述:{f.get('description', '')[:200]}" for f in unclassified[:10])
    prompt = f"""请为以下伏笔进行分类，以JSON数组格式输出：
```json
[
  {{"id": "伏笔ID", "category": "人物伏笔/情节伏笔/世界观伏笔/能力伏笔/情感伏笔"}}
]
```
伏笔列表：
{fs_text}
只输出JSON数组。"""

    try:
        result = await ai.generate_json("你是一位伏笔分类专家。只输出JSON数组。", prompt)
        if isinstance(result, dict):
            result = [result]
        for classified in result:
            for f in foreshadows:
                if f.get("id") == classified.get("id"):
                    f["category"] = classified.get("category", "未分类")
        return {"foreshadows": foreshadows, "current_phase": "foreshadows_classified"}
    except Exception as e:
        logger.error("classify_foreshadow failed: %s", e)
        return {"current_phase": "foreshadows_classified", "error": str(e)}


async def check_deadlines(state: NovelState) -> dict:
    """Check which foreshadows are approaching their reveal deadline."""
    foreshadows = state.get("foreshadows", [])
    current_idx = state.get("current_chapter_index", 0)

    warnings = []
    for f in foreshadows:
        target = f.get("target_chapter", 0)
        if target and target > 0:
            chapters_left = target - (current_idx + 1)
            if 1 <= chapters_left <= 5:
                warnings.append({
                    "foreshadow_id": f.get("id"),
                    "description": f.get("description", ""),
                    "target_chapter": target,
                    "chapters_left": chapters_left,
                    "warning": f"伏笔应在第{target}章前揭示，还剩{chapters_left}章",
                })
        # Also update resolved status
        if f.get("status") == "set" and f.get("set_chapter", 0) < current_idx - 10:
            f["status"] = "overdue"

    return {"foreshadows": foreshadows, "current_phase": "deadlines_checked",
            "_foreshadow_warnings": warnings}


async def generate_timeline(state: NovelState) -> dict:
    """Generate a timeline representation of all foreshadows."""
    foreshadows = state.get("foreshadows", [])
    if not foreshadows:
        return {"current_phase": "timeline_generated"}

    # Sort by set_chapter
    sorted_fs = sorted(foreshadows, key=lambda f: f.get("set_chapter", 0))
    timeline = []
    for f in sorted_fs:
        timeline.append({
            "chapter": f.get("set_chapter", "?"),
            "status": f.get("status", "unknown"),
            "category": f.get("category", "未分类"),
            "description": f.get("description", "")[:100],
        })

    return {"current_phase": "timeline_generated", "_foreshadow_timeline": timeline}


async def generate_statistics(state: NovelState) -> dict:
    """Generate foreshadow statistics by status, category, and chapter range."""
    foreshadows = state.get("foreshadows", [])

    status_counts = {"pending": 0, "set": 0, "resolved": 0, "abandoned": 0, "overdue": 0}
    category_counts = {}
    for f in foreshadows:
        status_counts[f.get("status", "pending")] = status_counts.get(f.get("status", "pending"), 0) + 1
        cat = f.get("category", "未分类")
        category_counts[cat] = category_counts.get(cat, 0) + 1

    return {
        "current_phase": "statistics_generated",
        "_foreshadow_stats": {
            "total": len(foreshadows),
            "by_status": status_counts,
            "by_category": category_counts,
            "resolution_rate": (status_counts["resolved"] / max(len(foreshadows), 1)) * 100,
        },
        "foreshadows": foreshadows,
    }


def create_foreshadow_subgraph():
    """Create the Foreshadow Management subgraph.
    Flow: sync → classify → check_deadlines → generate_timeline → generate_statistics
    """
    builder = StateGraph(NovelState)

    builder.add_node("sync_from_analysis", sync_from_analysis)
    builder.add_node("classify_foreshadow", classify_foreshadow)
    builder.add_node("check_deadlines", check_deadlines)
    builder.add_node("generate_timeline", generate_timeline)
    builder.add_node("generate_statistics", generate_statistics)

    builder.set_entry_point("sync_from_analysis")
    builder.add_edge("sync_from_analysis", "classify_foreshadow")
    builder.add_edge("classify_foreshadow", "check_deadlines")
    builder.add_edge("check_deadlines", "generate_timeline")
    builder.add_edge("generate_timeline", "generate_statistics")
    builder.add_edge("generate_statistics", END)

    return builder.compile()
