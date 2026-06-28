"""ExportSubGraph — triggerable agent for project data export.

Exports selected data (full project / characters / organizations) as structured JSON.
"""
from langgraph.graph import StateGraph, END, START
from app.graphs.state import NovelState
import json
import logging

logger = logging.getLogger(__name__)


async def export_full_project(state: NovelState) -> dict:
    """Export the full project as a structured JSON document."""
    export_data = {
        "title": state.get("title", ""),
        "description": state.get("description", ""),
        "genre": state.get("genre", ""),
        "narrative_perspective": state.get("narrative_perspective", ""),
        "target_words": state.get("target_words", 0),
        "world_setting": state.get("world_setting", {}),
        "outlines": state.get("outlines", []),
        "characters": state.get("characters", []),
        "relationships": state.get("relationships", []),
        "organizations": state.get("organizations", []),
        "careers": state.get("careers", []),
        "chapters": [
            {"chapter_index": ch.get("chapter_index", i), "title": ch.get("title", ""),
             "content": ch.get("content", ""), "word_count": ch.get("word_count", 0)}
            for i, ch in enumerate(state.get("chapters", []))
        ],
        "foreshadows": state.get("foreshadows", []),
        "writing_style_id": state.get("writing_style_id"),
        "active_skill": state.get("active_skill"),
    }
    return {
        "_export_data": export_data,
        "_export_json": json.dumps(export_data, ensure_ascii=False, indent=2),
        "current_phase": "export_complete",
    }


async def export_characters_only(state: NovelState) -> dict:
    """Export only character + relationship data."""
    data = {
        "characters": state.get("characters", []),
        "relationships": state.get("relationships", []),
    }
    return {
        "_export_data": data,
        "_export_json": json.dumps(data, ensure_ascii=False, indent=2),
        "current_phase": "export_complete",
    }


async def export_organizations_only(state: NovelState) -> dict:
    """Export only organization + career data."""
    data = {
        "organizations": state.get("organizations", []),
        "careers": state.get("careers", []),
    }
    return {
        "_export_data": data,
        "_export_json": json.dumps(data, ensure_ascii=False, indent=2),
        "current_phase": "export_complete",
    }


def _select_export_target(state: NovelState) -> str:
    """Conditional routing: choose export node based on mode."""
    mode = state.get("_export_mode", "full")
    if mode == "characters":
        return "export_characters_only"
    if mode == "organizations":
        return "export_organizations_only"
    return "export_full_project"


def create_export_subgraph():
    """Build the Export subgraph.

    Usage:
        state = {"project_id": "...", "_export_mode": "full|characters|organizations", ...}
        result = await export_subgraph.ainvoke(state)
        json_str = result["_export_json"]
    """
    builder = StateGraph(NovelState)

    builder.add_node("export_full_project", export_full_project)
    builder.add_node("export_characters_only", export_characters_only)
    builder.add_node("export_organizations_only", export_organizations_only)

    # Route from START to the appropriate export node
    builder.add_conditional_edges(
        START,
        _select_export_target,
        {
            "export_full_project": "export_full_project",
            "export_characters_only": "export_characters_only",
            "export_organizations_only": "export_organizations_only",
        },
    )

    builder.add_edge("export_full_project", END)
    builder.add_edge("export_characters_only", END)
    builder.add_edge("export_organizations_only", END)

    return builder.compile()
