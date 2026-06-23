"""LangGraph Status API — graph state snapshots, node timing, visualization data."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.graphs.main_graph import get_graph
from app.logger import get_logger

router = APIRouter(prefix="/graph-status", tags=["graph_status"])
logger = get_logger(__name__)


@router.get("/state/{project_id}")
async def get_graph_state(project_id: str):
    """Get the current LangGraph state snapshot for a project."""
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": f"project_{project_id}"}}
        state = await graph.aget_state(config)

        if state and state.values:
            values = dict(state.values)
            # Filter out large content fields for lightweight state view
            safe_state = {}
            for key in ("project_id", "title", "genre", "description", "narrative_perspective",
                        "project_status", "total_word_count", "current_chapter_index",
                        "current_phase", "writing_style_id", "active_skill", "error"):
                if key in values:
                    safe_state[key] = values[key]

            safe_state["outline_count"] = len(values.get("outlines", []))
            safe_state["character_count"] = len(values.get("characters", []))
            safe_state["chapter_count"] = len(values.get("chapters", []))
            safe_state["foreshadow_count"] = len(values.get("foreshadows", []))
            safe_state["inspiration_count"] = len(values.get("inspirations", []))

            return {
                "project_id": project_id,
                "current_phase": safe_state.get("current_phase", "unknown"),
                "state": safe_state,
                "checkpoint_id": state.metadata.get("step", -1) if state.metadata else -1,
            }

        return {"project_id": project_id, "current_phase": "not_started", "state": {}}

    except Exception as e:
        logger.exception("Failed to get graph state for %s", project_id)
        return {"project_id": project_id, "error": str(e)}


@router.get("/history/{project_id}")
async def get_state_history(project_id: str):
    """Get state checkpoint history for a project."""
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": f"project_{project_id}"}}

        checkpoints = []
        async for snapshot in graph.aget_state_history(config, limit=20):
            checkpoints.append({
                "step": snapshot.metadata.get("step", -1) if snapshot.metadata else -1,
                "phase": snapshot.values.get("current_phase", "unknown") if snapshot.values else "unknown",
            })

        return {"checkpoints": checkpoints}
    except Exception as e:
        logger.exception("Failed to get state history for %s", project_id)
        return {"checkpoints": [], "error": str(e)}


@router.get("/metrics/{project_id}")
async def get_node_metrics(project_id: str):
    """Get per-node execution timing metrics with aggregated statistics."""
    from app.graphs.metrics import get_project_metrics
    return get_project_metrics(project_id)


@router.get("/visualization/{project_id}")
async def get_graph_visualization(project_id: str):
    """Get graph structure data for frontend visualization (@xyflow/react).

    Returns nodes and edges reflecting the current project's execution state.
    """
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": f"project_{project_id}"}}
        state = await graph.aget_state(config)
        values = state.values if state else {}
        current_phase = values.get("current_phase", "not_started") if values else "not_started"

        _pipeline_order = [
            "project_init", "world_build", "outline_plan", "career_manage",
            "organization", "char_create", "chapter_write", "chapter_analyze",
            "memory_update", "foreshadow",
        ]

        def _completed_up_to(phase: str) -> int:
            """Return the index of the last completed pipeline node."""
            completions = {
                "project_init": 1, "world_build": 2, "outline_plan": 3,
                "career_manage": 4, "organization": 5, "char_create": 6,
                "memory_update_complete": 9, "foreshadow_complete": 10,
            }
            # Check chapter_write/analyze sub-phases
            if phase in ("context_built", "draft_generated", "chapter_write"):
                return 6  # char_create done, chapter_write in progress
            if phase in ("plot_extracted", "report_generated", "chapter_analyze"):
                return 7  # chapter_write done, chapter_analyze in progress
            if phase == "post_analysis_complete":
                return 8
            for key, idx in completions.items():
                if phase.endswith("_complete") and key in phase:
                    return idx
            return 0

        completed_idx = _completed_up_to(current_phase)

        def node_status(node_id: str) -> str:
            if current_phase == "not_started":
                return "pending"
            if node_id not in _pipeline_order:
                return "standby"
            node_idx = _pipeline_order.index(node_id)
            if node_idx < completed_idx:
                return "completed"
            if node_idx == completed_idx:
                return "active"
            return "pending"

        nodes = [
            {"id": "project_init", "type": "agent", "label": "项目初始化", "status": node_status("project_init")},
            {"id": "world_build", "type": "subgraph", "label": "世界观构建", "status": node_status("world_build")},
            {"id": "outline_plan", "type": "agent", "label": "大纲规划", "status": node_status("outline_plan")},
            {"id": "career_manage", "type": "agent", "label": "职业管理", "status": node_status("career_manage")},
            {"id": "organization", "type": "agent", "label": "组织管理", "status": node_status("organization")},
            {"id": "char_create", "type": "subgraph", "label": "角色创建", "status": node_status("char_create")},
            {"id": "chapter_write", "type": "subgraph", "label": "章节写作", "status": node_status("chapter_write")},
            {"id": "chapter_analyze", "type": "subgraph", "label": "章节分析", "status": node_status("chapter_analyze")},
            {"id": "memory_update", "type": "agent", "label": "记忆更新", "status": node_status("memory_update")},
            {"id": "foreshadow", "type": "subgraph", "label": "伏笔管理", "status": node_status("foreshadow")},
            {"id": "batch_gen", "type": "subgraph", "label": "批量操作", "status": "standby"},
            {"id": "review", "type": "subgraph", "label": "多Agent审稿", "status": "standby"},
            {"id": "export_data", "type": "subgraph", "label": "项目导出", "status": "standby"},
            {"id": "import_data", "type": "subgraph", "label": "项目导入", "status": "standby"},
            {"id": "cover_gen", "type": "subgraph", "label": "封面生成", "status": "standby"},
            {"id": "inspiration_gen", "type": "subgraph", "label": "灵感生成", "status": "standby"},
            {"id": "book_import", "type": "subgraph", "label": "拆书导入", "status": "standby"},
        ]

        edges = [
            {"source": "project_init", "target": "world_build"},
            {"source": "world_build", "target": "outline_plan"},
            {"source": "outline_plan", "target": "career_manage"},
            {"source": "career_manage", "target": "organization"},
            {"source": "organization", "target": "char_create"},
            {"source": "char_create", "target": "chapter_write"},
            {"source": "chapter_write", "target": "chapter_analyze"},
            {"source": "chapter_analyze", "target": "chapter_write", "label": "继续写作"},
            {"source": "chapter_analyze", "target": "memory_update", "label": "完成"},
            {"source": "memory_update", "target": "foreshadow"},
        ]

        return {"nodes": nodes, "edges": edges}

    except Exception as e:
        logger.exception("Failed to get visualization for %s", project_id)
        return {"nodes": [], "edges": [], "error": str(e)}
