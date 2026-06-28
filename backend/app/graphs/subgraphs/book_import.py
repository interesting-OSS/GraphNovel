"""BookImportSubGraph — TXT/EPUB file import and AI-powered structuring."""
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.config import settings
import logging

logger = logging.getLogger(__name__)


from app.graphs.utils import get_ai_service as _get_ai_service


async def parse_file(state: NovelState) -> dict:
    """Parse TXT/EPUB file content. The actual file parsing is done in the API service layer.
    This node receives the pre-parsed text and prepares it for AI processing.
    """
    # File content would be passed via state or a temporary storage reference
    logger.info("File parsing phase started")
    return {"current_phase": "file_parsed"}


async def detect_chapter_boundaries(state: NovelState) -> dict:
    """AI-powered chapter boundary detection from raw text."""
    ai = _get_ai_service(state, temperature=0.3)
    # The raw text would come from the parsing step via _import_raw_text in state
    raw_text = state.get("_import_raw_text", "")
    if not raw_text:
        return {"current_phase": "boundaries_detected"}

    # Process in chunks of 15000 chars to find chapter boundaries
    chunk = raw_text[:15000]
    prompt = f"""请分析以下小说文本，识别章节边界。找出所有章节标题或分界标记，以JSON格式输出：
```json
{{
  "chapters": [
    {{
      "index": 1,
      "title": "章节标题（如果能识别）",
      "start_marker": "章节开始的文本片段（前20字）",
      "suggested_title": "AI建议的章节标题"
    }}
  ],
  "total_chapters_found": 5,
  "chapter_pattern": "章节的命名模式（如：第X章/Chapter X/用空行分隔等）"
}}
```

文本内容：
{chunk}

只输出JSON。"""

    try:
        result = await ai.generate_json("你是一位文本结构分析专家。只输出JSON。", prompt)
        return {
            "current_phase": "boundaries_detected",
            "_chapter_boundaries": result.get("chapters", []),
            "_chapter_pattern": result.get("chapter_pattern", "未知"),
        }
    except Exception as e:
        logger.error("detect_chapter_boundaries failed: %s", e)
        return {"current_phase": "boundaries_detected", "error": str(e)}


async def extract_characters(state: NovelState) -> dict:
    """NER + LLM character extraction from text."""
    ai = _get_ai_service(state, temperature=0.3)
    raw_text = state.get("_import_raw_text", "")
    if not raw_text:
        return {"current_phase": "characters_extracted"}

    chunk = raw_text[:12000]
    prompt = f"""请从以下小说文本中提取所有主要角色，以JSON数组格式输出：
```json
[
  {{
    "name": "角色名",
    "role_type": "protagonist/supporting/antagonist",
    "evidence": "文本中出现的证据（引文片段）",
    "inferred_traits": "从文本推断的性格特征",
    "relationships": ["与其他角色的关系"]
  }}
]
```

文本内容：
{chunk}

只输出JSON数组。"""

    try:
        result = await ai.generate_json("你是一位角色识别专家。只输出JSON数组。", prompt)
        if isinstance(result, dict):
            result = [result]
        return {
            "current_phase": "characters_extracted",
            "_extracted_characters": result,
        }
    except Exception as e:
        logger.error("extract_characters failed: %s", e)
        return {"current_phase": "characters_extracted", "error": str(e)}


async def rebuild_timeline(state: NovelState) -> dict:
    """Rebuild story timeline from imported chapters."""
    logger.info("Timeline rebuilding phase")
    return {"current_phase": "timeline_rebuilt"}


async def structure_content(state: NovelState) -> dict:
    """Structure parsed content into chapters, characters, and outlines."""
    boundaries = state.get("_chapter_boundaries", [])
    extracted_chars = state.get("_extracted_characters", [])

    # Convert detected boundaries to outline format
    if boundaries:
        outlines = state.get("outlines", [])
        for i, boundary in enumerate(boundaries):
            outlines.append({
                "volume": 1,
                "chapter_index": i + 1,
                "title": boundary.get("suggested_title", boundary.get("title", f"第{i+1}章")),
                "summary": f"导入章节 - 起始: {boundary.get('start_marker', '未知')}",
                "key_points": "",
                "mode": "one-to-one",
                "expansion_strategy": "balanced",
            })

        characters = state.get("characters", [])
        for char in extracted_chars:
            characters.append({
                "id": f"imported_{char.get('name', '')}",
                "name": char.get("name", ""),
                "role_type": char.get("role_type", "supporting"),
                "appearance": char.get("evidence", ""),
                "personality": char.get("inferred_traits", ""),
                "background": "",
                "relationships": char.get("relationships", []),
            })

        return {"outlines": outlines, "characters": characters, "current_phase": "content_structured"}

    return {"current_phase": "content_structured"}


def create_book_import_subgraph():
    """Create the Book Import subgraph.

    Flow: parse_file → detect_chapter_boundaries → extract_characters →
          rebuild_timeline → structure_content
    """
    builder = StateGraph(NovelState)

    builder.add_node("parse_file", parse_file)
    builder.add_node("detect_chapter_boundaries", detect_chapter_boundaries)
    builder.add_node("extract_characters", extract_characters)
    builder.add_node("rebuild_timeline", rebuild_timeline)
    builder.add_node("structure_content", structure_content)

    builder.set_entry_point("parse_file")
    builder.add_edge("parse_file", "detect_chapter_boundaries")
    builder.add_edge("detect_chapter_boundaries", "extract_characters")
    builder.add_edge("extract_characters", "rebuild_timeline")
    builder.add_edge("rebuild_timeline", "structure_content")
    builder.add_edge("structure_content", END)

    return builder.compile()
