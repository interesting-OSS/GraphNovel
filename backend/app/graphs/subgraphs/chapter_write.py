"""ChapterWriteSubGraph — the core chapter writing pipeline with real AI."""
from typing import Literal, Optional, AsyncGenerator
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.agents.writer_agent import WriterAgent
from app.agents.editor_agent import EditorAgent
from app.memory.context_builder import ContextBuilder
from app.graphs.nodes.retrieval import RetrievalNode
from app.config import settings
import logging

logger = logging.getLogger(__name__)


async def build_context(state: NovelState) -> dict:
    """Assemble writing context: RAG retrieval + layered memory + outline + characters."""
    world = state.get("world_setting", {})
    characters = state.get("characters", [])
    outlines = state.get("outlines", [])
    current_idx = state.get("current_chapter_index", 0)
    foreshadows = state.get("foreshadows", [])
    chapters = state.get("chapters", [])

    # ── Step 1: RAG retrieval from vector memory ──
    retrieved_texts = []
    try:
        retrieval = RetrievalNode(
            n_results=8,
            layers=["mid_term", "long_term"],  # skip short_term (current chapter already in context)
        )
        retrieval_result = await retrieval(state)
        memories = retrieval_result.get("_retrieved_memories", [])
        retrieved_texts = [m.get("content", "") for m in memories if m.get("content")]
        logger.info("RAG retrieved %d memories for chapter %d", len(retrieved_texts), current_idx + 1)
    except Exception as exc:
        logger.warning("RAG retrieval skipped: %s", exc)

    # ── Step 2: Build structured context ──
    context = ContextBuilder.build_full_context(
        world_setting=world,
        characters=characters,
        outlines=outlines,
        current_chapter_index=current_idx,
        active_foreshadows=foreshadows,
        previous_chapter_content=chapters[-1].get("content", "") if chapters else None,
        retrieved_memories=retrieved_texts if retrieved_texts else None,
    )

    # Get the current chapter outline
    current_outline = {}
    if 0 <= current_idx < len(outlines):
        current_outline = outlines[current_idx]

    context["current_outline"] = current_outline
    context["genre"] = state.get("genre", "玄幻")
    context["writing_style"] = state.get("writing_style_id", "默认风格")
    context["narrative_perspective"] = state.get("narrative_perspective", "第三人称")

    logger.info("Chapter %d writing context built", current_idx + 1)
    return {"current_phase": "context_built", "_writing_context": context}


async def generate_draft(state: NovelState, *, writer: Optional[WriterAgent] = None) -> dict:
    """Generate the chapter draft via LLM."""
    ai = _get_ai_service(state)
    context = state.get("_writing_context", {})
    current_outline = context.get("current_outline", {})
    genre = context.get("genre", "玄幻")

    writer_agent = writer or WriterAgent(model=ai._get_model())
    prompt = writer_agent.build_writing_prompt(
        genre=genre,
        world_summary=context.get("world_summary", "暂无世界观设定"),
        volume_outline=context.get("outline_context", "暂无大纲"),
        characters_context=context.get("characters_context", "暂无角色信息"),
        active_foreshadows=context.get("foreshadow_context", "暂无活跃伏笔"),
        previous_chapter_summary=context.get("previous_chapter", "这是第一章，无前文"),
        writing_style=context.get("writing_style", "默认风格"),
        continuation_mode=_get_continuation_mode(state),
        chapter_outline=current_outline.get("summary", current_outline.get("title", "请根据大纲进行创作")),
    )

    try:
        # Use non-streaming for graph node execution
        # Streaming is handled at the API level via astream_events
        result = await ai.generate(writer_agent.system_prompt, prompt)

        chapters = state.get("chapters", [])
        current_idx = state.get("current_chapter_index", 0)
        new_chapter = {
            "index": current_idx,
            "title": current_outline.get("title", f"第{current_idx + 1}章"),
            "content": result.strip(),
            "word_count": len(result),
            "status": "draft",
            "writing_style_id": state.get("writing_style_id"),
            "narrative_perspective_override": state.get("narrative_perspective"),
        }

        # Update or append chapter
        if 0 <= current_idx < len(chapters):
            chapters[current_idx] = new_chapter
        else:
            chapters.append(new_chapter)

        return {
            "chapters": chapters,
            "current_phase": "draft_generated",
            "total_word_count": sum(c.get("word_count", 0) for c in chapters),
        }
    except Exception as e:
        logger.error("generate_draft failed for chapter %d: %s", current_idx + 1, e)
        return {"current_phase": "draft_generated", "error": str(e)}


async def apply_feedback(state: NovelState) -> dict:
    """Apply user feedback to modify the chapter. Uses AgentNode for retry + metrics."""
    from app.graphs.nodes.agents import AgentNode
    ai = _get_ai_service(state)
    chapters = state.get("chapters", [])
    current_idx = state.get("current_chapter_index", 0)

    if not (0 <= current_idx < len(chapters) and chapters[current_idx].get("content")):
        return {"current_phase": "feedback_applied", "human_feedback": None}

    editor = EditorAgent(model=ai.model)
    chapter_content = chapters[current_idx]["content"]
    feedback = state.get("human_feedback", "请改善文笔")

    # Use AgentNode for automatic retry, error handling, and metrics tracking
    async def build_feedback_prompt(s: NovelState, agent) -> str:
        return agent.build_rewrite_prompt(
            original_text=chapter_content,
            feedback=feedback,
            rewrite_mode="custom",
        )

    async def handle_feedback_result(s: NovelState, result_text: str) -> dict:
        chs = list(s.get("chapters", []))
        idx = s.get("current_chapter_index", 0)
        if 0 <= idx < len(chs):
            chs[idx] = {**chs[idx], "content": result_text.strip(),
                        "status": "draft", "word_count": len(result_text)}
        return {"chapters": chs, "current_phase": "feedback_applied", "human_feedback": None}

    agent_node = AgentNode(
        agent=editor,
        prompt_builder=build_feedback_prompt,
        result_handler=handle_feedback_result,
        max_retries=2,
    )
    return await agent_node(state)


async def rewrite_partial(state: NovelState) -> dict:
    """Partial rewrite of selected text."""
    ai = _get_ai_service(state)
    feedback = state.get("human_feedback", "请重写选中段落")
    chapters = state.get("chapters", [])
    current_idx = state.get("current_chapter_index", 0)

    if 0 <= current_idx < len(chapters) and chapters[current_idx].get("content"):
        editor = EditorAgent(model=ai._get_model())
        chapter_content = chapters[current_idx]["content"]
        prompt = editor.build_rewrite_prompt(
            original_text=chapter_content,
            feedback=feedback,
            rewrite_mode="partial",
        )
        try:
            result = await ai.generate(editor.system_prompt, prompt)
            chapters[current_idx]["content"] = result.strip()
            chapters[current_idx]["status"] = "draft"
            chapters[current_idx]["word_count"] = len(result)
            return {"chapters": chapters, "current_phase": "partial_rewrite_done", "human_feedback": None}
        except Exception as e:
            logger.error("rewrite_partial failed: %s", e)
            return {"current_phase": "partial_rewrite_done", "human_feedback": None, "error": str(e)}

    return {"current_phase": "partial_rewrite_done", "human_feedback": None}


async def rewrite_full(state: NovelState) -> dict:
    """Full chapter rewrite based on user feedback."""
    ai = _get_ai_service(state)
    feedback = state.get("human_feedback", "请完全重写本章")
    chapters = state.get("chapters", [])
    current_idx = state.get("current_chapter_index", 0)
    context = state.get("_writing_context", {})

    if 0 <= current_idx < len(chapters) and chapters[current_idx].get("content"):
        editor = EditorAgent(model=ai._get_model())
        chapter_content = chapters[current_idx]["content"]
        prompt = editor.build_rewrite_prompt(
            original_text=chapter_content,
            feedback=feedback,
            rewrite_mode="full",
        )
        try:
            result = await ai.generate(editor.system_prompt, prompt)
            chapters[current_idx]["content"] = result.strip()
            chapters[current_idx]["status"] = "draft"
            chapters[current_idx]["word_count"] = len(result)
            return {"chapters": chapters, "current_phase": "full_rewrite_done", "human_feedback": None}
        except Exception as e:
            logger.error("rewrite_full failed: %s", e)
            return {"current_phase": "full_rewrite_done", "human_feedback": None, "error": str(e)}

    return {"current_phase": "full_rewrite_done", "human_feedback": None}


async def polish_text(state: NovelState) -> dict:
    """Polish the chapter prose: adjust pacing, dialogue, description ratios."""
    ai = _get_ai_service(state)
    chapters = state.get("chapters", [])
    current_idx = state.get("current_chapter_index", 0)

    if 0 <= current_idx < len(chapters) and chapters[current_idx].get("content"):
        editor = EditorAgent(model=ai._get_model())
        chapter_content = chapters[current_idx]["content"]
        prompt = editor.build_polish_prompt(original_text=chapter_content)
        try:
            result = await ai.generate(editor.system_prompt, prompt)
            chapters[current_idx]["content"] = result.strip()
            chapters[current_idx]["status"] = "polished"
            chapters[current_idx]["word_count"] = len(result)
            return {"chapters": chapters, "current_phase": "polish_done", "human_feedback": None}
        except Exception as e:
            logger.error("polish_text failed: %s", e)
            return {"current_phase": "polish_done", "human_feedback": None, "error": str(e)}

    return {"current_phase": "polish_done", "human_feedback": None}


async def save_generation_history(state: NovelState) -> dict:
    """Save the generation version and compute diff."""
    chapters = state.get("chapters", [])
    current_idx = state.get("current_chapter_index", 0)
    history = state.get("generation_history", [])

    if 0 <= current_idx < len(chapters):
        chapter = chapters[current_idx]
        version = len([h for h in history if h.get("chapter_index") == current_idx]) + 1
        import uuid
        history.append({
            "id": str(uuid.uuid4()),
            "chapter_index": current_idx,
            "version": version,
            "content": chapter.get("content", ""),
            "created_at": None,  # Will be set by DB layer
        })

    return {
        "generation_history": history,
        "current_phase": "history_saved",
        "current_chapter_index": current_idx + 1,  # Advance to next chapter
    }


async def human_review(state: NovelState) -> dict:
    """Interrupt point for user review after draft generation.

    This node is a pass-through — the actual pause happens via
    interrupt_before=["human_review"] in the compiled subgraph.
    When the user resumes with a Command(resume=...), human_feedback
    is already set in state, and route_review handles the routing.
    """
    current_idx = state.get("current_chapter_index", 0)
    logger.info("Human review checkpoint for chapter %d", current_idx + 1)
    return {"current_phase": "awaiting_review"}


def route_review(state: NovelState) -> Literal["approved", "feedback", "partial_rewrite", "full_rewrite", "polish"]:
    """Route based on user review decision after human_review interrupt."""
    feedback = state.get("human_feedback", "")

    # Route based on user feedback
    if feedback == "polish":
        return "polish"
    if feedback == "full_rewrite":
        return "full_rewrite"
    if feedback == "partial_rewrite":
        return "partial_rewrite"
    if feedback == "approved":
        return "approved"
    # Empty feedback means user hasn't reviewed yet — go to approved
    # (this path is taken after polish/rewrite nodes route back through generate_draft)
    if not feedback:
        return "approved"
    return "feedback"


def _get_continuation_mode(state: NovelState) -> str:
    """Extract continuation mode from state."""
    return state.get("generation_config", {}).get("continuation_mode", "auto")


def _get_ai_service(state: NovelState, **overrides):
    """Get an AI service instance from state generation config."""
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


def create_chapter_write_subgraph():
    """Create the Chapter Writing subgraph.

    Flow:
        build_context → generate_draft → human_review (interrupt)
        ├── approved → save_history → (exit)
        ├── feedback → apply_feedback → generate_draft → human_review
        ├── partial_rewrite → rewrite_partial → generate_draft → human_review
        ├── full_rewrite → rewrite_full → generate_draft → human_review
        └── polish → polish_text → generate_draft → human_review
    """
    builder = StateGraph(NovelState)

    builder.add_node("build_context", build_context)
    builder.add_node("generate_draft", generate_draft)
    builder.add_node("human_review", human_review)
    builder.add_node("apply_feedback", apply_feedback)
    builder.add_node("rewrite_partial", rewrite_partial)
    builder.add_node("rewrite_full", rewrite_full)
    builder.add_node("polish_text", polish_text)
    builder.add_node("save_generation_history", save_generation_history)

    builder.set_entry_point("build_context")
    builder.add_edge("build_context", "generate_draft")
    builder.add_edge("generate_draft", "human_review")

    builder.add_conditional_edges(
        "human_review",
        route_review,
        {
            "approved": "save_generation_history",
            "feedback": "apply_feedback",
            "partial_rewrite": "rewrite_partial",
            "full_rewrite": "rewrite_full",
            "polish": "polish_text",
        }
    )

    builder.add_edge("apply_feedback", "generate_draft")
    builder.add_edge("rewrite_partial", "generate_draft")
    builder.add_edge("rewrite_full", "generate_draft")
    builder.add_edge("polish_text", "generate_draft")

    builder.add_edge("save_generation_history", END)

    return builder.compile(interrupt_before=["human_review"])
