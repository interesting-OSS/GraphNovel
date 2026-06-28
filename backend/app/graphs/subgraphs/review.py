"""ReviewSubGraph — multi-agent review pipeline with parallel AI analysis."""
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.logic_agent import LogicAgent
from app.agents.prose_agent import ProseAgent
from app.agents.pacing_agent import PacingAgent
from app.config import settings
import logging

logger = logging.getLogger(__name__)


from app.graphs.utils import get_ai_service as _get_ai_service


def _get_chapter_content(state: NovelState) -> str:
    chapters = state.get("chapters", [])
    chapter_index = state.get("current_chapter_index", 0)
    if 0 <= chapter_index < len(chapters):
        return chapters[chapter_index].get("content", "")
    return ""


async def reader_review(state: NovelState) -> dict:
    """Review from reader perspective."""
    ai = _get_ai_service(state, temperature=0.5, max_tokens=8000)
    content = _get_chapter_content(state)
    if not content:
        return {"current_phase": "reader_reviewed"}

    agent = ReviewerAgent(model=ai.model)
    prompt = agent.build_review_prompt(chapter_content=content[:10000])
    try:
        result = await ai.generate(agent.system_prompt, prompt)
        reviews = state.get("_review_results", {})
        reviews["reader_review"] = result.strip()
        return {"current_phase": "reader_reviewed", "_review_results": reviews}
    except Exception as e:
        logger.error("reader_review failed: %s", e)
        return {"current_phase": "reader_reviewed", "error": str(e)}


async def logic_check(state: NovelState) -> dict:
    """Check plot logic consistency."""
    ai = _get_ai_service(state, temperature=0.5, max_tokens=8000)
    content = _get_chapter_content(state)
    if not content:
        return {"current_phase": "logic_checked"}

    world = state.get("world_setting", {})
    world_str = "\n".join(f"{k}: {v[:200]}" for k, v in world.items() if v)
    chars = state.get("characters", [])
    chars_str = "\n".join(f"- {c.get('name', '')}: {c.get('personality', '')}" for c in chars[:5])
    analyses = state.get("chapter_analyses", [])
    prev_events = analyses[-1].get("summary", "无") if analyses else "无"

    agent = LogicAgent(model=ai.model)
    prompt = agent.build_check_prompt(
        chapter_content=content[:10000],
        world_setting=world_str,
        characters_info=chars_str,
        previous_events=prev_events,
    )
    try:
        result = await ai.generate(agent.system_prompt, prompt)
        reviews = state.get("_review_results", {})
        reviews["logic_check"] = result.strip()
        return {"current_phase": "logic_checked", "_review_results": reviews}
    except Exception as e:
        logger.error("logic_check failed: %s", e)
        return {"current_phase": "logic_checked", "error": str(e)}


async def prose_check(state: NovelState) -> dict:
    """Check prose quality."""
    ai = _get_ai_service(state, temperature=0.5, max_tokens=8000)
    content = _get_chapter_content(state)
    if not content:
        return {"current_phase": "prose_checked"}

    agent = ProseAgent(model=ai.model)
    prompt = agent.build_check_prompt(chapter_content=content[:10000])
    try:
        result = await ai.generate(agent.system_prompt, prompt)
        reviews = state.get("_review_results", {})
        reviews["prose_check"] = result.strip()
        return {"current_phase": "prose_checked", "_review_results": reviews}
    except Exception as e:
        logger.error("prose_check failed: %s", e)
        return {"current_phase": "prose_checked", "error": str(e)}


async def pacing_check(state: NovelState) -> dict:
    """Analyze pacing."""
    ai = _get_ai_service(state, temperature=0.5, max_tokens=8000)
    content = _get_chapter_content(state)
    if not content:
        return {"current_phase": "pacing_checked"}

    outlines = state.get("outlines", [])
    chapter_index = state.get("current_chapter_index", 0)
    agent = PacingAgent(model=ai.model)
    prompt = agent.build_check_prompt(
        chapter_content=content[:10000],
        chapter_index=chapter_index + 1,
        total_chapters=len(outlines),
        story_phase="发展阶段",
    )
    try:
        result = await ai.generate(agent.system_prompt, prompt)
        reviews = state.get("_review_results", {})
        reviews["pacing_check"] = result.strip()
        return {"current_phase": "pacing_checked", "_review_results": reviews}
    except Exception as e:
        logger.error("pacing_check failed: %s", e)
        return {"current_phase": "pacing_checked", "error": str(e)}


async def aggregate_reviews(state: NovelState) -> dict:
    """Aggregate all four review dimensions into a unified review report."""
    reviews = state.get("_review_results", {})
    chapter_index = state.get("current_chapter_index", 0)

    report = f"""# 第{chapter_index + 1}章 多Agent审稿报告

## 📖 读者视角
{reviews.get("reader_review", "无读者审阅")}

## 🔍 逻辑一致性检查
{reviews.get("logic_check", "无逻辑检查")}

## ✍️ 文笔质量检查
{reviews.get("prose_check", "无文笔检查")}

## ⏱️ 节奏分析
{reviews.get("pacing_check", "无节奏分析")}
"""
    chapter_analyses = state.get("chapter_analyses", [])
    for a in chapter_analyses:
        if a.get("chapter_index") == chapter_index:
            a["review_report"] = report
            break

    return {"chapter_analyses": chapter_analyses, "current_phase": "reviews_aggregated",
            "_review_results": {}}


def create_review_subgraph():
    """Create the Multi-Agent Review subgraph.

    Four review agents run sequentially → aggregate into final report.
    """
    builder = StateGraph(NovelState)

    builder.add_node("reader_review", reader_review)
    builder.add_node("logic_check", logic_check)
    builder.add_node("prose_check", prose_check)
    builder.add_node("pacing_check", pacing_check)
    builder.add_node("aggregate_reviews", aggregate_reviews)

    builder.set_entry_point("reader_review")
    builder.add_edge("reader_review", "logic_check")
    builder.add_edge("logic_check", "prose_check")
    builder.add_edge("prose_check", "pacing_check")
    builder.add_edge("pacing_check", "aggregate_reviews")
    builder.add_edge("aggregate_reviews", END)

    return builder.compile()
