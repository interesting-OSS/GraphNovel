"""NovelCreationGraph — top-level orchestration graph for the novel creation pipeline."""
from typing import Literal, Optional
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState

# PostgresSaver is optional — only needed for production persistence
PostgresSaver = None
try:
    from langgraph.checkpoint.postgres import PostgresSaver
except ImportError:
    pass
from app.services.ai_service import create_ai_service
from app.config import settings

from app.graphs.subgraphs.world_build import create_world_build_subgraph
from app.graphs.subgraphs.chapter_write import create_chapter_write_subgraph
from app.graphs.subgraphs.chapter_analyze import create_chapter_analyze_subgraph
from app.graphs.subgraphs.char_create import create_char_create_subgraph
from app.graphs.subgraphs.batch_gen import create_batch_gen_subgraph
from app.graphs.subgraphs.review import create_review_subgraph
from app.graphs.subgraphs.foreshadow import create_foreshadow_subgraph
from app.graphs.subgraphs.cover_gen import create_cover_gen_subgraph
from app.graphs.subgraphs.inspiration import create_inspiration_subgraph
from app.graphs.subgraphs.book_import import create_book_import_subgraph
from app.graphs.subgraphs.export_data import create_export_subgraph
from app.graphs.subgraphs.import_data import create_import_subgraph

import logging
import json

logger = logging.getLogger(__name__)


def _record_metric(project_id: str, node: str, phase: str, start: float, ok: bool, err: str = ""):
    """Record node timing metric (best-effort, never throws)."""
    try:
        from app.graphs.metrics import record_node_execution
        record_node_execution(project_id, node, phase, start, ok, err)
    except Exception:
        pass


from app.graphs.utils import get_ai_service as _get_ai_service


# ============= Core nodes =============


async def project_init_node(state: NovelState) -> dict:
    """Initialize project: generate title, description, and metadata via AI."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    title = state.get("title", "")
    description = state.get("description", "")
    feedback = state.get("human_feedback", "")
    project_id = state.get("project_id", "unknown")
    t0 = __import__("time").time()

    if not title or not description:
        prompt = f"""用户想要创作一部{genre}小说。{feedback}

请帮助完善项目设定，以JSON格式输出：
```json
{{
  "title": "小说标题（8-20字）",
  "description": "一句话简介（30-80字）",
  "narrative_perspective": "第一人称/第三人称/多视角",
  "genre_refined": "更精确的类型标签",
  "theme_keywords": ["主题词1", "主题词2", "主题词3"]
}}
```"""
        try:
            result = await ai.generate_json(
                "你是一位资深的出版编辑，擅长为小说命名和撰写简介。只输出JSON。", prompt)
            _record_metric(project_id, "project_init", state.get("current_phase", ""), t0, True)

            new_title = result.get("title", title)
            new_desc = result.get("description", description)
            new_genre = result.get("genre_refined", genre)
            new_perspective = result.get("narrative_perspective", "第三人称")

            # Sync to DB
            from app.graphs.graph_db_sync import sync_project_init
            await sync_project_init(project_id, new_title, new_desc, new_genre, new_perspective)

            return {
                "title": new_title,
                "description": new_desc,
                "narrative_perspective": new_perspective,
                "genre": new_genre,
                "current_phase": "project_init_complete",
            }
        except Exception as e:
            logger.error("project_init failed: %s", e)
            _record_metric(project_id, "project_init", state.get("current_phase", ""), t0, False, str(e))
            return {"current_phase": "project_init_complete", "error": str(e)}

    _record_metric(project_id, "project_init", state.get("current_phase", ""), t0, True)
    return {"current_phase": "project_init_complete"}


async def outline_plan_node(state: NovelState) -> dict:
    """Plan the outline structure: generate volume and chapter structure via AI."""
    ai = _get_ai_service(state)
    title = state.get("title", "")
    genre = state.get("genre", "玄幻")
    description = state.get("description", "")
    target_words = state.get("target_words", 100000)
    world = state.get("world_setting", {})
    characters = state.get("characters", [])
    outline_mode = state.get("outline_mode", "one-to-one")
    project_id = state.get("project_id", "unknown")
    t0 = __import__("time").time()

    chars_summary = "\n".join(
        f"- {c.get('name', '')}（{c.get('role_type', '')}）：{c.get('goals', '')}"
        for c in characters[:5]
    ) if characters else "暂无角色"

    prompt = f"""小说标题：{title}
类型：{genre}
简介：{description}
目标字数：{target_words:,}字
大纲模式：{outline_mode}

世界观概要：
{json.dumps({k: world.get(k, '')[:100] for k in ['time_period', 'power_system', 'factions']}, ensure_ascii=False)}

角色概要：
{chars_summary}

请规划小说大纲，以JSON格式输出：
```json
{{
  "volumes": 3,
  "total_chapters": 60,
  "outlines": [
    {{
      "volume": 1,
      "chapter_index": 1,
      "title": "章节标题",
      "summary": "章节内容摘要（50-150字）",
      "key_points": "关键情节要点",
      "target_words": 3000,
      "mode": "one-to-one",
      "expansion_strategy": "balanced"
    }}
  ]
}}
```

要求：
1. 根据目标字数合理分配章节数（平均每章2000-4000字）
2. 前三章必须详细规划
3. 整体结构遵循：开端→发展→转折→高潮→结局
4. 大纲模式为one-to-many时，每个大纲节点可对应多章
只输出JSON。"""

    try:
        result = await ai.generate_json("你是一位资深的小说结构规划师。只输出JSON。", prompt)
        outlines = result.get("outlines", [])
        _record_metric(project_id, "outline_plan", state.get("current_phase", ""), t0, True)

        # Sync to DB
        from app.graphs.graph_db_sync import sync_outlines
        await sync_outlines(project_id, outlines)

        return {
            "outlines": outlines,
            "current_phase": "outline_plan_complete",
        }
    except Exception as e:
        logger.error("outline_plan failed: %s", e)
        _record_metric(project_id, "outline_plan", state.get("current_phase", ""), t0, False, str(e))
        return {"current_phase": "outline_plan_complete", "error": str(e)}


async def career_manage_node(state: NovelState) -> dict:
    """Manage career/level systems: generate career structures via AI."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    world = state.get("world_setting", {})
    project_id = state.get("project_id", "unknown")
    t0 = __import__("time").time()

    prompt = f"""小说类型：{genre}
力量体系：{world.get('power_system', '未设定')}

请为这部小说设计职业等级体系，以JSON数组格式输出：
```json
[
  {{
    "id": "career_1",
    "name": "修仙者",
    "type": "主要职业",
    "description": "职业描述",
    "levels": [
      {{"name": "炼气期", "index": 1, "description": "等级描述", "abilities": ["能力1", "能力2"]}},
      {{"name": "筑基期", "index": 2, "description": "等级描述", "abilities": ["能力1"]}}
    ]
  }}
]
```

为{genre}类型设计1-3个主要职业体系，每个职业包含5-10个等级。只输出JSON数组。"""

    try:
        result = await ai.generate_json("你是一位游戏/小说职业体系设计师。只输出JSON数组。", prompt)
        if isinstance(result, dict):
            result = [result]
        _record_metric(project_id, "career_manage", state.get("current_phase", ""), t0, True)

        # Sync to DB
        from app.graphs.graph_db_sync import sync_careers
        await sync_careers(project_id, result)

        return {
            "careers": result,
            "current_phase": "career_manage_complete",
        }
    except Exception as e:
        logger.error("career_manage failed: %s", e)
        _record_metric(project_id, "career_manage", state.get("current_phase", ""), t0, False, str(e))
        return {"current_phase": "career_manage_complete", "error": str(e)}


async def organization_node(state: NovelState) -> dict:
    """Manage organizations and factions: generate via AI."""
    ai = _get_ai_service(state)
    genre = state.get("genre", "玄幻")
    world = state.get("world_setting", {})
    project_id = state.get("project_id", "unknown")
    t0 = __import__("time").time()

    prompt = f"""小说类型：{genre}
世界观势力：{world.get('factions', '未设定')}

请为这部小说设计组织/门派/势力体系，以JSON数组格式输出：
```json
[
  {{
    "id": "org_1",
    "name": "组织名",
    "type": "门派/家族/商会/势力/国家",
    "description": "组织描述（50-100字）",
    "goal": "组织目标",
    "hierarchy": ["层级1", "层级2", "层级3"],
    "leader_name": "首领名称（暂定）",
    "members": ["成员1", "成员2"],
    "alignment": "正义/中立/邪恶"
  }}
]
```

设计3-6个主要组织，各组织之间要有利益冲突或联盟关系。只输出JSON数组。"""

    try:
        result = await ai.generate_json("你是一位世界观设计师。只输出JSON数组。", prompt)
        if isinstance(result, dict):
            result = [result]
        _record_metric(project_id, "organization", state.get("current_phase", ""), t0, True)

        # Sync to DB
        from app.graphs.graph_db_sync import sync_organizations
        await sync_organizations(project_id, result)

        return {
            "organizations": result,
            "current_phase": "organization_complete",
        }
    except Exception as e:
        logger.error("organization failed: %s", e)
        _record_metric(project_id, "organization", state.get("current_phase", ""), t0, False, str(e))
        return {"current_phase": "organization_complete", "error": str(e)}


async def memory_update_node(state: NovelState) -> dict:
    """Mark the memory update phase as complete.

    Actual memory operations (SQL + ChromaDB vector store) are performed by
    AnalysisPipeline.run_full_pipeline() during the chapter_analyze subgraph's
    post_analysis_pipeline step. This node serves as a phase marker for the
    main graph flow.
    """
    chapter_index = state.get("current_chapter_index", 0)
    logger.info("Memory update phase marked for chapter %d", chapter_index)
    return {"current_phase": "memory_update_complete"}


async def foreshadow_node(state: NovelState) -> dict:
    """Synchronize foreshadow status from chapter analysis.

    Marks recently set/resolved foreshadows and prepares the state
    for the next chapter or batch operation.
    """
    foreshadows = state.get("foreshadows", [])
    chapter_analyses = state.get("chapter_analyses", [])
    chapter_index = state.get("current_chapter_index", 0)

    # Foreshadows are already synced in the chapter_analyze subgraph
    # This node just ensures the state is consistent before proceeding
    active_count = sum(1 for f in foreshadows if f.get("status") == "set")
    resolved_count = sum(1 for f in foreshadows if f.get("status") == "resolved")
    logger.info("Foreshadow status: %d active, %d resolved, heading to chapter %d",
                active_count, resolved_count, chapter_index)

    return {"current_phase": "foreshadow_complete"}


# ============= Conditional routing =============


def should_continue_writing(state: NovelState) -> Literal["chapter_write", "end"]:
    """Determine if there are more chapters to write."""
    outlines = state.get("outlines", [])
    current = state.get("current_chapter_index", 0)
    if current < len(outlines):
        return "chapter_write"
    return "end"


def should_do_batch(state: NovelState) -> Literal["batch_gen", "memory_update"]:
    """Check if batch generation is requested."""
    batch_tasks = state.get("background_tasks", [])
    has_batch = any(t.get("type") == "batch_generate" for t in batch_tasks if isinstance(t, dict))
    return "batch_gen" if has_batch else "memory_update"


# ============= Graph construction =============


def create_novel_graph(checkpointer: Optional[PostgresSaver] = None):
    """Build the full NovelCreationGraph with all subgraphs and conditional routing.

    Graph structure:
        ProjectInit → WorldBuild → OutlinePlan → CareerManage →
        Organization → CharCreate → ChapterWrite ⇄ ChapterAnalyze ⇄
        PolishEdit → MemoryUpdate → Foreshadow → (loop or end)

    Parallel subgraphs (triggerable anytime):
        Inspiration, Foreshadow, BookImport, CoverGen, Review
    """
    builder = StateGraph(NovelState)

    # === Core Nodes ===
    builder.add_node("project_init", project_init_node)
    builder.add_node("world_build", create_world_build_subgraph())
    builder.add_node("outline_plan", outline_plan_node)
    builder.add_node("career_manage", career_manage_node)
    builder.add_node("organization", organization_node)
    builder.add_node("char_create", create_char_create_subgraph())
    builder.add_node("chapter_write", create_chapter_write_subgraph())
    builder.add_node("chapter_analyze", create_chapter_analyze_subgraph())
    builder.add_node("memory_update", memory_update_node)
    builder.add_node("foreshadow", foreshadow_node)
    builder.add_node("batch_gen", create_batch_gen_subgraph())
    builder.add_node("review", create_review_subgraph())
    builder.add_node("foreshadow_mgmt", create_foreshadow_subgraph())
    builder.add_node("cover_gen", create_cover_gen_subgraph())
    builder.add_node("inspiration_gen", create_inspiration_subgraph())
    builder.add_node("book_import", create_book_import_subgraph())
    builder.add_node("export_data", create_export_subgraph())
    builder.add_node("import_data", create_import_subgraph())

    # === Edges: Main Creation Pipeline ===
    builder.add_edge("project_init", "world_build")
    builder.add_edge("world_build", "outline_plan")
    builder.add_edge("outline_plan", "career_manage")
    builder.add_edge("career_manage", "organization")
    builder.add_edge("organization", "char_create")

    # Connect character creation to chapter writing
    builder.add_edge("char_create", "chapter_write")

    # After chapter write, go to analyze
    builder.add_edge("chapter_write", "chapter_analyze")

    # After analysis, branch: continue writing or finish
    builder.add_conditional_edges(
        "chapter_analyze",
        should_continue_writing,
        {
            "chapter_write": "chapter_write",
            "end": "memory_update",
        }
    )

    builder.add_edge("memory_update", "foreshadow")

    # After foreshadow, check if batch needed → or END
    builder.add_conditional_edges(
        "foreshadow",
        should_do_batch,
        {
            "batch_gen": "batch_gen",
            "memory_update": END,
        }
    )

    builder.add_edge("batch_gen", END)
    builder.add_edge("review", END)
    builder.add_edge("foreshadow_mgmt", END)
    builder.add_edge("cover_gen", END)
    builder.add_edge("inspiration_gen", END)
    builder.add_edge("book_import", END)
    builder.add_edge("export_data", END)
    builder.add_edge("import_data", END)

    # === Set entry point ===
    builder.set_entry_point("project_init")

    from langgraph.checkpoint.memory import MemorySaver
    # === Compile with interrupt for human review ===
    graph = builder.compile(
        checkpointer=checkpointer if checkpointer else MemorySaver(),
        interrupt_before=["chapter_write"],
    )

    return graph


# ============= Singleton =============

_graph_instance = None


def get_graph():
    """Get or create the novel graph singleton with optional Postgres persistence."""
    global _graph_instance
    if _graph_instance is None:
        logger_local = logging.getLogger(__name__)
        checkpointer = None
        try:
            if settings.database_url:
                sync_url = settings.database_url.replace("+asyncpg", "")
                cp = PostgresSaver.from_conn_string(sync_url)
                cp.setup()
                checkpointer = cp
                logger_local.info("PostgresSaver checkpointer initialized successfully")
        except Exception as e:
            logger_local.warning("PostgresSaver unavailable, running without persistence: %s", e)
        _graph_instance = create_novel_graph(checkpointer)
    return _graph_instance
