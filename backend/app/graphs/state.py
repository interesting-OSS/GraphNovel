"""NovelState — the complete state schema for the novel creation graph."""
from typing import TypedDict, List, Optional, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class NovelState(TypedDict, total=False):
    # === Project Metadata ===
    project_id: str
    title: str
    description: Optional[str]
    genre: str
    target_words: int
    narrative_perspective: str
    project_status: str  # planning / writing / revising / completed
    total_word_count: int
    outline_mode: str  # one-to-one / one-to-many
    cover_prompt: Optional[str]
    cover_url: Optional[str]

    # === World Setting ===
    world_setting: dict  # {time_period, geography, power_system, factions, culture, rules}

    # === Outline ===
    outlines: List[dict]

    # === Characters ===
    characters: List[dict]
    relationships: List[dict]
    organizations: List[dict]
    careers: List[dict]

    # === Chapters ===
    current_chapter_index: int
    chapters: List[dict]

    # === Memory & Context ===
    plot_memory: List[dict]
    chapter_analyses: List[dict]
    foreshadows: List[dict]

    # === Generation History ===
    generation_history: List[dict]

    # === Background Tasks ===
    background_tasks: List[dict]

    # === Messages ===
    messages: Annotated[List[BaseMessage], add_messages]

    # === Control Flow ===
    current_phase: str
    human_feedback: Optional[str]
    generation_config: dict  # {provider, model, api_key, temperature, max_tokens, stream, ...}
    error: Optional[str]

    # === Inspiration ===
    inspirations: List[dict]

    # === Writing Style / Skills ===
    active_skill: Optional[str]
    writing_style_id: Optional[str]
    prompt_template_id: Optional[str]


def create_initial_state(
    project_id: str = "",
    title: str = "",
    genre: str = "玄幻",
    target_words: int = 100000,
    narrative_perspective: str = "第三人称",
    generation_config: Optional[dict] = None,
) -> NovelState:
    """Create the initial state for a new novel creation session."""
    return NovelState(
        project_id=project_id,
        title=title,
        description=None,
        genre=genre,
        target_words=target_words,
        narrative_perspective=narrative_perspective,
        project_status="planning",
        total_word_count=0,
        outline_mode="one-to-one",
        cover_prompt=None,
        cover_url=None,
        world_setting={},
        outlines=[],
        characters=[],
        relationships=[],
        organizations=[],
        careers=[],
        current_chapter_index=0,
        chapters=[],
        plot_memory=[],
        chapter_analyses=[],
        foreshadows=[],
        generation_history=[],
        background_tasks=[],
        messages=[],
        current_phase="init",
        human_feedback=None,
        generation_config=generation_config or {
            "provider": "openai",
            "model": "gpt-4o",
            "temperature": 0.7,
            "max_tokens": 32000,
            "stream": True,
        },
        error=None,
        inspirations=[],
        active_skill=None,
        writing_style_id=None,
        prompt_template_id=None,
    )
