"""ChapterAnalyzeSubGraph — multi-dimensional chapter analysis with real AI."""
from langgraph.graph import StateGraph, END
from app.graphs.state import NovelState
from app.services.ai_service import create_ai_service
from app.config import settings
import json
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
        max_tokens=overrides.pop("max_tokens", config.get("max_tokens", 32000)),
        **overrides,
    )


def _get_current_chapter(state: NovelState) -> dict:
    chapters = state.get("chapters", [])
    idx = state.get("current_chapter_index", 0)
    if 0 <= idx < len(chapters):
        return chapters[idx]
    return {}


def _get_previous_summary(state: NovelState) -> str:
    analyses = state.get("chapter_analyses", [])
    if analyses:
        return analyses[-1].get("summary", "无前章分析")
    return "无前章分析"


async def extract_plot(state: NovelState) -> dict:
    """Extract plot points, conflicts, and story progression."""
    ai = _get_ai_service(state)
    chapter = _get_current_chapter(state)
    content = chapter.get("content", "")
    if not content:
        return {"current_phase": "plot_extracted"}

    prompt = f"""请从以下章节中提取情节信息，以JSON格式输出：
```json
{{
  "plot_points": [
    {{"description": "情节描述", "importance": 7, "impact": 6}}
  ],
  "conflict_info": {{
    "type": "角色冲突/内部冲突/社会冲突",
    "participants": ["角色A", "角色B"],
    "level": 3,
    "resolution_progress": 30
  }},
  "story_phase": "build_up/climax/resolution"
}}
```

章节内容：
{content[:8000]}"""

    try:
        result = await ai.generate_json("你是一位专业的小说分析师。只输出JSON。", prompt)
        chapter_analyses = state.get("chapter_analyses", [])
        idx = state.get("current_chapter_index", 0)
        analysis = {"chapter_index": idx, "plot_points": result.get("plot_points", []),
                     "conflict_info": result.get("conflict_info", {}), "story_phase": result.get("story_phase", "")}
        # Update or append
        updated = False
        for i, a in enumerate(chapter_analyses):
            if a.get("chapter_index") == idx:
                chapter_analyses[i].update(analysis)
                updated = True
                break
        if not updated:
            chapter_analyses.append(analysis)
        return {"chapter_analyses": chapter_analyses, "current_phase": "plot_extracted"}
    except Exception as e:
        logger.error("extract_plot failed: %s", e)
        return {"current_phase": "plot_extracted", "error": str(e)}


async def extract_foreshadows(state: NovelState) -> dict:
    """Identify foreshadows, hooks, and Chekhov's guns."""
    ai = _get_ai_service(state)
    chapter = _get_current_chapter(state)
    content = chapter.get("content", "")
    if not content:
        return {"current_phase": "foreshadows_extracted"}

    prompt = f"""请从以下章节中识别伏笔和钩子，以JSON格式输出：
```json
{{
  "new_foreshadows": [
    {{"description": "伏笔描述", "category": "人物伏笔/情节伏笔/世界观伏笔/能力伏笔", "importance": 7}}
  ],
  "resolved_foreshadows": ["被回收的伏笔描述"],
  "hooks": [
    {{"description": "钩子描述", "type": "悬念/反转/转折", "impact": 5}}
  ]
}}
```

章节内容：
{content[:8000]}"""

    try:
        result = await ai.generate_json("你是一位专业的小说分析师，善于识别伏笔和钩子。只输出JSON。", prompt)
        idx = state.get("current_chapter_index", 0)
        # Sync new foreshadows to state
        existing = state.get("foreshadows", [])
        for fs in result.get("new_foreshadows", []):
            existing.append({
                "id": str(len(existing) + 1),
                "description": fs.get("description", ""),
                "status": "set",
                "category": fs.get("category", "情节伏笔"),
                "set_chapter": idx + 1,
                "importance": fs.get("importance", 5),
            })
        # Mark resolved
        for resolved_desc in result.get("resolved_foreshadows", []):
            for f in existing:
                if resolved_desc in f.get("description", ""):
                    f["status"] = "resolved"

        # Add hooks to chapter analysis
        chapter_analyses = state.get("chapter_analyses", [])
        for a in chapter_analyses:
            if a.get("chapter_index") == idx:
                a["hooks"] = result.get("hooks", [])
                break

        return {"foreshadows": existing, "chapter_analyses": chapter_analyses,
                "current_phase": "foreshadows_extracted"}
    except Exception as e:
        logger.error("extract_foreshadows failed: %s", e)
        return {"current_phase": "foreshadows_extracted", "error": str(e)}


async def extract_hooks(state: NovelState) -> dict:
    """Extract hooks and cliffhangers (already done in extract_foreshadows)."""
    return {"current_phase": "hooks_extracted"}


async def track_character_arc(state: NovelState) -> dict:
    """Track character arc progression and status changes."""
    ai = _get_ai_service(state)
    chapter = _get_current_chapter(state)
    content = chapter.get("content", "")
    characters = state.get("characters", [])
    if not content or not characters:
        return {"current_phase": "character_arc_tracked"}

    char_names = ", ".join([c.get("name", "") for c in characters[:10]])
    prompt = f"""请追踪以下角色在本章中的弧光进展和状态变更，以JSON格式输出：
```json
{{
  "character_changes": [
    {{
      "character_name": "角色名",
      "mental_state_change": "心理状态变化描述",
      "power_level_change": "能力/等级变化（如有）",
      "relationship_changes": ["关系变化描述"],
      "key_decisions": ["关键决策"],
      "arc_progress": "角色弧光的整体进展"
    }}
  ],
  "entity_changes": [
    {{"type": "career_upgrade/organization_change/status_change", "character": "角色名", "description": "变更描述"}}
  ]
}}
```

角色列表：{char_names}

章节内容：
{content[:8000]}"""

    try:
        result = await ai.generate_json("你是一位专业的角色弧光分析师。只输出JSON。", prompt)
        idx = state.get("current_chapter_index", 0)
        chapter_analyses = state.get("chapter_analyses", [])
        for a in chapter_analyses:
            if a.get("chapter_index") == idx:
                a["character_changes"] = result.get("character_changes", [])
                a["entity_changes"] = result.get("entity_changes", [])
                break
        return {"chapter_analyses": chapter_analyses, "current_phase": "character_arc_tracked"}
    except Exception as e:
        logger.error("track_character_arc failed: %s", e)
        return {"current_phase": "character_arc_tracked", "error": str(e)}


async def analyze_emotional_arc(state: NovelState) -> dict:
    """Analyze emotional arc: primary emotion, intensity, trajectory."""
    ai = _get_ai_service(state)
    chapter = _get_current_chapter(state)
    content = chapter.get("content", "")
    if not content:
        return {"current_phase": "emotional_arc_analyzed"}

    prompt = f"""请分析以下章节的情感弧线，以JSON格式输出：
```json
{{
  "primary_emotion": "主要情绪",
  "intensity": 0.7,
  "trajectory": ["开始情绪", "转折情绪", "结尾情绪"],
  "secondary_emotions": ["次要情绪1", "次要情绪2"],
  "emotional_turning_points": ["情感转折点描述"],
  "reader_emotional_impact": "预期对读者的情感影响"
}}
```

章节内容：
{content[:8000]}"""

    try:
        result = await ai.generate_json("你是一位情感分析专家。只输出JSON。", prompt)
        idx = state.get("current_chapter_index", 0)
        chapter_analyses = state.get("chapter_analyses", [])
        for a in chapter_analyses:
            if a.get("chapter_index") == idx:
                a["emotional_arc"] = result
                break
        return {"chapter_analyses": chapter_analyses, "current_phase": "emotional_arc_analyzed"}
    except Exception as e:
        logger.error("analyze_emotional_arc failed: %s", e)
        return {"current_phase": "emotional_arc_analyzed", "error": str(e)}


async def analyze_pacing(state: NovelState) -> dict:
    """Analyze pacing: score, dialogue/description/narrative ratios."""
    ai = _get_ai_service(state)
    chapter = _get_current_chapter(state)
    content = chapter.get("content", "")
    if not content:
        return {"current_phase": "pacing_analyzed"}

    outlines = state.get("outlines", [])
    idx = state.get("current_chapter_index", 0)

    prompt = f"""请分析以下章节的节奏，以JSON格式输出：
```json
{{
  "pacing_score": 7,
  "dialogue_ratio": 0.3,
  "description_ratio": 0.35,
  "narrative_ratio": 0.35,
  "section_pacing": [
    {{"section": "开头", "pace": "快/中/慢", "effect": "效果评价"}}
  ],
  "rhythm_assessment": "整体节奏评估",
  "suggestions": ["节奏优化建议"]
}}
```

全书第{idx + 1}章 / 共{len(outlines)}章

章节内容：
{content[:8000]}"""

    try:
        result = await ai.generate_json("你是一位节奏分析专家。只输出JSON。", prompt)
        idx = state.get("current_chapter_index", 0)
        chapter_analyses = state.get("chapter_analyses", [])
        for a in chapter_analyses:
            if a.get("chapter_index") == idx:
                a["pacing"] = result
                break
        return {"chapter_analyses": chapter_analyses, "current_phase": "pacing_analyzed"}
    except Exception as e:
        logger.error("analyze_pacing failed: %s", e)
        return {"current_phase": "pacing_analyzed", "error": str(e)}


async def assess_quality(state: NovelState) -> dict:
    """Assess overall quality using AnalystAgent: engagement, coherence, composite score, suggestions."""
    from app.agents.analyst_agent import AnalystAgent
    ai = _get_ai_service(state)
    chapter = _get_current_chapter(state)
    content = chapter.get("content", "")
    if not content:
        return {"current_phase": "quality_assessed"}

    # Use AnalystAgent's structured prompt builder for quality assessment
    analyst = AnalystAgent()
    idx = state.get("current_chapter_index", 0)
    chapter_analyses = state.get("chapter_analyses", [])
    analysis_data = {}
    for a in chapter_analyses:
        if a.get("chapter_index") == idx:
            analysis_data = a
            break

    previous_summary = analysis_data.get("summary", "前章分析未完成")
    foreshadows = state.get("foreshadows", [])
    active_fs = ", ".join([f.get("description", "") for f in foreshadows if f.get("status") == "set"][:5])
    characters = state.get("characters", [])
    chars_info = ", ".join([f"{c.get('name', '')}({c.get('mental_state', '')})" for c in characters[:5]])

    prompt = analyst.build_analysis_prompt(
        chapter_content=content[:8000],
        previous_summary=previous_summary,
        active_foreshadows=active_fs or "无",
        characters_info=chars_info or "无",
    )

    try:
        result = await ai.generate_json(
            analyst.system_prompt + "\n只输出JSON。", prompt)
        for a in chapter_analyses:
            if a.get("chapter_index") == idx:
                a["quality"] = result
                break
        return {"chapter_analyses": chapter_analyses, "current_phase": "quality_assessed"}
    except Exception as e:
        logger.error("assess_quality failed: %s", e)
        return {"current_phase": "quality_assessed", "error": str(e)}


async def generate_summary(state: NovelState) -> dict:
    """Generate a structured chapter summary for the memory system."""
    ai = _get_ai_service(state)
    chapter = _get_current_chapter(state)
    content = chapter.get("content", "")
    if not content:
        return {"current_phase": "summary_generated"}

    prompt = f"""请为以下章节生成一个结构化的摘要（200-400字），包含：
1. 本章核心事件
2. 角色动态
3. 关键转折点
4. 伏笔/钩子设置

章节内容：
{content[:8000]}

只输出纯文本摘要："""

    try:
        result = await ai.generate("你是一位精于概括的小说分析师。", prompt)
        summary = result.strip()
        idx = state.get("current_chapter_index", 0)
        chapter_analyses = state.get("chapter_analyses", [])
        for a in chapter_analyses:
            if a.get("chapter_index") == idx:
                a["summary"] = summary
                break

        # Also add to plot_memory for RAG retrieval
        plot_memory = state.get("plot_memory", [])
        plot_memory.append({
            "chapter_index": idx,
            "summary": summary,
            "timestamp": None,
        })

        return {"chapter_analyses": chapter_analyses, "plot_memory": plot_memory,
                "current_phase": "summary_generated"}
    except Exception as e:
        logger.error("generate_summary failed: %s", e)
        return {"current_phase": "summary_generated", "error": str(e)}


async def generate_report(state: NovelState) -> dict:
    """Generate a comprehensive natural-language analysis report (Markdown)."""
    idx = state.get("current_chapter_index", 0)
    chapter_analyses = state.get("chapter_analyses", [])
    analysis_data = {}
    for a in chapter_analyses:
        if a.get("chapter_index") == idx:
            analysis_data = a
            break

    if not analysis_data:
        analysis_data = {"summary": "分析数据不足"}

    quality = analysis_data.get("quality", {})
    pacing = analysis_data.get("pacing", {})
    emotional = analysis_data.get("emotional_arc", {})
    plot_points = analysis_data.get("plot_points", [])
    hooks = analysis_data.get("hooks", [])

    report = f"""# 第{idx + 1}章 综合分析报告

## 一、摘要
{analysis_data.get('summary', '暂无摘要')}

## 二、质量评估
- **综合评分**: {quality.get('quality_score', 'N/A')}/10
- **读者参与度**: {quality.get('engagement_score', 'N/A')}/10
- **连贯性**: {quality.get('coherence_score', 'N/A')}/10

### 优点
{chr(10).join('- ' + s for s in quality.get('strengths', ['暂无']))}

### 改进方向
{chr(10).join('- ' + s for s in quality.get('suggestions', ['暂无']))}

## 三、情节分析
### 核心情节要点
{chr(10).join(f"- {p.get('description', '')} (重要性: {p.get('importance', 'N/A')}/10)" for p in plot_points[:5])}

## 四、节奏分析
- **节奏评分**: {pacing.get('pacing_score', 'N/A')}/10
- **对话占比**: {pacing.get('dialogue_ratio', 'N/A')}
- **描写占比**: {pacing.get('description_ratio', 'N/A')}
- **叙事占比**: {pacing.get('narrative_ratio', 'N/A')}

## 五、情感分析
- **主情绪**: {emotional.get('primary_emotion', 'N/A')}
- **情绪强度**: {emotional.get('intensity', 'N/A')}
- **情感走向**: {' → '.join(emotional.get('trajectory', ['暂无']))}

## 六、钩子
{chr(10).join(f"- {h.get('description', '')} (类型: {h.get('type', 'N/A')})" for h in (hooks or [])[:5])}
"""
    for a in chapter_analyses:
        if a.get("chapter_index") == idx:
            a["report"] = report
            break

    return {"chapter_analyses": chapter_analyses, "current_phase": "report_generated"}


async def post_analysis_pipeline_node(state: NovelState) -> dict:
    """Run the automatic post-analysis pipeline after analysis completes.

    Updates: character mental_state, career progress, foreshadow lifecycle,
    dual-write memory (SQL + ChromaDB), relationships.
    Each step is independently error-handled — one failure doesn't block others.
    """
    from app.services.analysis_pipeline import analysis_pipeline
    from app.database import async_session_factory

    project_id = state.get("project_id", "")
    chapter_index = state.get("current_chapter_index", 0)
    chapters = state.get("chapters", [])
    chapter_id = ""
    if 0 <= chapter_index < len(chapters):
        chapter_id = chapters[chapter_index].get("id", "")

    # Collect all analysis results from the current state
    chapter_analyses = state.get("chapter_analyses", [])
    analysis_data = {}
    if chapter_analyses and chapter_index < len(chapter_analyses):
        analysis_data = chapter_analyses[chapter_index]
    elif chapter_analyses:
        analysis_data = chapter_analyses[-1]

    if not analysis_data or not project_id:
        logger.warning("Post-analysis skipped: no analysis data or project_id")
        return {"current_phase": "post_analysis_skipped"}

    db = None
    try:
        async with async_session_factory() as db:
            results = await analysis_pipeline.run_full_pipeline(
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_index=chapter_index,
                analysis_data=analysis_data,
                db=db,
            )

        logger.info(
            "Post-analysis complete for ch%d: chars=%s careers=%s foreshadows=%s mem=%s rels=%s",
            chapter_index,
            results.get("character_states", {}).get("characters_updated", 0),
            results.get("career_progress", {}).get("career_updates", 0),
            results.get("foreshadow_management", {}).get("foreshadows_planted", 0),
            results.get("memory_sync", {}).get("sql_records", 0),
            results.get("relationship_updates", {}).get("relationships_updated", 0),
        )

        return {
            "current_phase": "post_analysis_complete",
            "_post_analysis_results": results,
        }
    except Exception as e:
        logger.exception("Post-analysis pipeline failed entirely: %s", e)
        return {"current_phase": "post_analysis_error", "error": str(e)}


def create_chapter_analyze_subgraph():
    """Create the Chapter Analysis subgraph.

    Runs analysis followed by automatic post-analysis pipeline:
        extract_plot → extract_foreshadows → extract_hooks →
        track_character_arc → analyze_emotional_arc → analyze_pacing →
        assess_quality → generate_summary → generate_report →
        post_analysis_pipeline (auto-update characters/careers/foreshadows/memory)
    """
    builder = StateGraph(NovelState)

    builder.add_node("extract_plot", extract_plot)
    builder.add_node("extract_foreshadows", extract_foreshadows)
    builder.add_node("extract_hooks", extract_hooks)
    builder.add_node("track_character_arc", track_character_arc)
    builder.add_node("analyze_emotional_arc", analyze_emotional_arc)
    builder.add_node("analyze_pacing", analyze_pacing)
    builder.add_node("assess_quality", assess_quality)
    builder.add_node("generate_summary", generate_summary)
    builder.add_node("generate_report", generate_report)
    builder.add_node("post_analysis_pipeline", post_analysis_pipeline_node)

    builder.set_entry_point("extract_plot")
    builder.add_edge("extract_plot", "extract_foreshadows")
    builder.add_edge("extract_foreshadows", "extract_hooks")
    builder.add_edge("extract_hooks", "track_character_arc")
    builder.add_edge("track_character_arc", "analyze_emotional_arc")
    builder.add_edge("analyze_emotional_arc", "analyze_pacing")
    builder.add_edge("analyze_pacing", "assess_quality")
    builder.add_edge("assess_quality", "generate_summary")
    builder.add_edge("generate_summary", "generate_report")
    builder.add_edge("generate_report", "post_analysis_pipeline")
    builder.add_edge("post_analysis_pipeline", END)

    return builder.compile()
