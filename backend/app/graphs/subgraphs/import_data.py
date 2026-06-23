"""ImportSubGraph — triggerable agent for project data import.

Imports JSON data (full project / characters / organizations) and merges into state.
"""
from langgraph.graph import StateGraph, END, START
from app.graphs.state import NovelState
import logging

logger = logging.getLogger(__name__)


async def import_full_project(state: NovelState) -> dict:
    """Import a full project from JSON, merging into the current state."""
    import_data = state.get("_import_data", {})
    if not import_data:
        return {"current_phase": "import_error", "error": "No import data provided"}

    updates = {"current_phase": "import_complete"}

    # Merge top-level metadata (don't overwrite project_id)
    for key in ("title", "description", "genre", "narrative_perspective", "target_words"):
        if key in import_data:
            updates[key] = import_data[key]

    # Merge collections
    for key in ("world_setting", "outlines", "characters", "relationships",
                "organizations", "careers", "chapters", "foreshadows"):
        if key in import_data and isinstance(import_data[key], list):
            existing = state.get(key, [])
            updates[key] = existing + import_data[key]
        elif key in import_data and isinstance(import_data[key], dict):
            updates[key] = import_data[key]

    if "writing_style_id" in import_data:
        updates["writing_style_id"] = import_data["writing_style_id"]
    if "active_skill" in import_data:
        updates["active_skill"] = import_data["active_skill"]

    count = len(import_data.get("chapters", []))
    logger.info("Imported full project with %d chapters", count)
    return updates


async def import_characters_only(state: NovelState) -> dict:
    """Import character cards (characters + relationships)."""
    import_data = state.get("_import_data", {})
    updates = {"current_phase": "import_complete"}

    if "characters" in import_data:
        existing = state.get("characters", [])
        updates["characters"] = existing + import_data["characters"]
    if "relationships" in import_data:
        existing = state.get("relationships", [])
        updates["relationships"] = existing + import_data["relationships"]

    logger.info("Imported %d characters", len(import_data.get("characters", [])))
    return updates


async def import_organizations_only(state: NovelState) -> dict:
    """Import organization cards (organizations + careers)."""
    import_data = state.get("_import_data", {})
    updates = {"current_phase": "import_complete"}

    if "organizations" in import_data:
        existing = state.get("organizations", [])
        updates["organizations"] = existing + import_data["organizations"]
    if "careers" in import_data:
        existing = state.get("careers", [])
        updates["careers"] = existing + import_data["careers"]

    logger.info("Imported %d organizations", len(import_data.get("organizations", [])))
    return updates


async def import_validate(state: NovelState) -> dict:
    """Validate import data before applying."""
    import_data = state.get("_import_data", {})
    if not import_data:
        return {"current_phase": "import_error", "error": "No import data provided"}
    if not isinstance(import_data, dict):
        return {"current_phase": "import_error", "error": "Import data must be a JSON object"}
    return {"error": None}  # Clear any pre-existing error from previous graph steps


def _select_import_target(state: NovelState) -> str:
    mode = state.get("_import_mode", "full")
    if mode == "characters":
        return "import_characters_only"
    if mode == "organizations":
        return "import_organizations_only"
    return "import_full_project"


def _after_validate(state: NovelState) -> str:
    if state.get("error"):
        return END
    return _select_import_target(state)


def create_import_subgraph():
    """Build the Import subgraph.

    Usage:
        state = {"project_id": "...", "_import_mode": "full|characters|organizations",
                 "_import_data": {...}, ...}
        result = await import_subgraph.ainvoke(state)
    """
    builder = StateGraph(NovelState)

    builder.add_node("import_validate", import_validate)
    builder.add_node("import_full_project", import_full_project)
    builder.add_node("import_characters_only", import_characters_only)
    builder.add_node("import_organizations_only", import_organizations_only)

    builder.add_edge(START, "import_validate")

    builder.add_conditional_edges(
        "import_validate",
        _after_validate,
        {
            "import_full_project": "import_full_project",
            "import_characters_only": "import_characters_only",
            "import_organizations_only": "import_organizations_only",
            END: END,
        },
    )

    builder.add_edge("import_full_project", END)
    builder.add_edge("import_characters_only", END)
    builder.add_edge("import_organizations_only", END)

    return builder.compile()
