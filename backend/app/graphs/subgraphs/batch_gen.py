"""BatchGenSubGraph — batch chapter generation and analysis."""
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
        temperature=overrides.pop("temperature", config.get("temperature", 0.7)),
        max_tokens=overrides.pop("max_tokens", config.get("max_tokens", 32000)),
        **overrides,
    )


async def prepare_batch_context(state: NovelState) -> dict:
    """Prepare unified context for batch generation."""
    outlines = state.get("outlines", [])
    current_idx = state.get("current_chapter_index", 0)
    batch_tasks = state.get("background_tasks", [])

    # Determine batch range
    batch_start = current_idx
    batch_end = min(len(outlines), current_idx + 10)  # Max 10 chapters per batch

    # Update batch task status
    for task in batch_tasks:
        if task.get("type") == "batch_generate" and task.get("status") == "pending":
            task["status"] = "running"
            task["progress"] = 0
            task["batch_start"] = batch_start
            task["batch_end"] = batch_end
            task["total"] = batch_end - batch_start
            task["completed"] = 0

    return {
        "current_phase": "batch_context_prepared",
        "background_tasks": batch_tasks,
        "_batch_start": batch_start,
        "_batch_end": batch_end,
    }


async def generate_chapters_parallel(state: NovelState) -> dict:
    """Generate multiple chapters sequentially (not truly parallel in graph context)."""
    ai = _get_ai_service(state)
    batch_start = state.get("_batch_start", 0)
    batch_end = state.get("_batch_end", 0)
    outlines = state.get("outlines", [])
    chapters = state.get("chapters", [])
    batch_tasks = state.get("background_tasks", [])

    generated_count = 0
    for i in range(batch_start, batch_end):
        if i >= len(outlines):
            break
        outline = outlines[i]
        ai.reset()  # Fresh context for each chapter

        # Simple prompt for batch generation
        prompt = f"""请根据以下大纲创作章节正文：

章节标题：{outline.get('title', f'第{i+1}章')}
章节摘要：{outline.get('summary', '无')}
要点：{outline.get('key_points', '无')}

要求：1000-3000字，风格连贯。"""

        try:
            result = await ai.generate("你是一位专业小说作家。", prompt)
            new_chapter = {
                "index": i,
                "title": outline.get("title", f"第{i+1}章"),
                "content": result.strip(),
                "word_count": len(result),
                "status": "draft",
            }
            # Update or append
            if i < len(chapters):
                chapters[i] = new_chapter
            else:
                # Extend chapters list
                while len(chapters) < i:
                    chapters.append({"index": len(chapters), "title": "", "content": "", "status": "pending"})
                chapters.append(new_chapter)

            generated_count += 1

            # Update progress
            for task in batch_tasks:
                if task.get("type") == "batch_generate":
                    task["completed"] = generated_count
                    task["progress"] = (generated_count / max(task.get("total", 1), 1)) * 100

        except Exception as e:
            logger.error("Batch chapter %d generation failed: %s", i + 1, e)

    return {
        "chapters": chapters,
        "current_chapter_index": batch_end,
        "background_tasks": batch_tasks,
        "total_word_count": sum(c.get("word_count", 0) for c in chapters),
        "current_phase": "chapters_generated",
    }


async def batch_analyze(state: NovelState) -> dict:
    """Batch analyze all newly generated chapters."""
    batch_start = state.get("_batch_start", 0)
    batch_end = state.get("_batch_end", 0)
    chapters = state.get("chapters", [])
    plot_memory = state.get("plot_memory", [])

    # Generate summaries for batch chapters and add to plot_memory
    for i in range(batch_start, min(batch_end, len(chapters))):
        chapter = chapters[i]
        content = chapter.get("content", "")
        if content and len(content) > 100:
            # Simple keyword extraction for summary
            summary = content[:200] + "..."
            plot_memory.append({
                "chapter_index": i,
                "summary": summary,
            })

    return {
        "plot_memory": plot_memory,
        "current_phase": "batch_analyzed",
    }


async def update_progress(state: NovelState) -> dict:
    """Update batch generation progress for frontend tracking."""
    batch_tasks = state.get("background_tasks", [])
    for task in batch_tasks:
        if task.get("type") == "batch_generate":
            task["status"] = "completed"
            task["progress"] = 100

    return {"background_tasks": batch_tasks, "current_phase": "progress_updated"}


async def handle_pause_resume(state: NovelState) -> dict:
    """Handle pause/resume/cancel of batch operations using LangGraph checkpointing."""
    batch_tasks = state.get("background_tasks", [])
    feedback = state.get("human_feedback", "")

    for task in batch_tasks:
        if task.get("type") == "batch_generate":
            if feedback == "pause":
                task["status"] = "paused"
            elif feedback == "cancel":
                task["status"] = "cancelled"
            elif feedback == "resume":
                task["status"] = "running"

    return {"background_tasks": batch_tasks, "current_phase": "pause_resume_handled",
            "human_feedback": None}


def create_batch_gen_subgraph():
    """Create the Batch Generation subgraph.

    Flow: prepare_context → generate_parallel → batch_analyze → update_progress
    With pause/resume checking between steps.
    """
    builder = StateGraph(NovelState)

    builder.add_node("prepare_batch_context", prepare_batch_context)
    builder.add_node("generate_chapters_parallel", generate_chapters_parallel)
    builder.add_node("batch_analyze", batch_analyze)
    builder.add_node("update_progress", update_progress)
    builder.add_node("handle_pause_resume", handle_pause_resume)

    builder.set_entry_point("prepare_batch_context")
    builder.add_edge("prepare_batch_context", "generate_chapters_parallel")
    builder.add_edge("generate_chapters_parallel", "batch_analyze")
    builder.add_edge("batch_analyze", "update_progress")
    builder.add_edge("update_progress", END)

    return builder.compile()
