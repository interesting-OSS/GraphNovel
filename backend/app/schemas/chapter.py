"""Chapter schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ChapterCreate(BaseModel):
    """Request: create a chapter."""
    project_id: str = Field(..., description="所属项目ID")
    index: int = Field(..., description="章节序号")
    title: str = Field("新章节", description="章节标题")
    content: str = Field("", description="章节内容")
    word_count: int = Field(0, description="字数")
    status: str = Field("draft", description="章节状态: draft/polished/final")
    outline_id: Optional[str] = Field(None, description="关联大纲ID")
    writing_style_id: Optional[str] = Field(None, description="单章覆盖写作风格")
    model_override: Optional[str] = Field(None, description="单章覆盖AI模型")
    skill_override: Optional[str] = Field(None, description="单章覆盖技能包")
    narrative_perspective_override: Optional[str] = Field(None, description="单章覆盖叙述视角")


class ChapterUpdate(BaseModel):
    """Request: update a chapter."""
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[str] = None
    word_count: Optional[int] = None
    outline_id: Optional[str] = None
    writing_style_id: Optional[str] = None
    model_override: Optional[str] = None
    skill_override: Optional[str] = None
    narrative_perspective_override: Optional[str] = None


class ChapterResponse(BaseModel):
    """Response: chapter details."""
    id: str
    project_id: str
    outline_id: Optional[str] = None
    index: int
    title: str
    content: Optional[str] = None
    word_count: int
    status: str
    writing_style_id: Optional[str] = None
    model_override: Optional[str] = None
    skill_override: Optional[str] = None
    narrative_perspective_override: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChapterListResponse(BaseModel):
    """Response: paginated chapter list."""
    total: int
    items: list[ChapterResponse]


class ChapterGenerateRequest(BaseModel):
    """Request: AI generate a chapter."""
    project_id: str
    current_chapter_index: int = 0
    genre: str = "玄幻"
    outlines: list[dict] = Field(default_factory=list)
    characters: list[dict] = Field(default_factory=list)
    chapters: list[dict] = Field(default_factory=list)
    world_setting: dict = Field(default_factory=dict)
    foreshadows: list[dict] = Field(default_factory=list)
    plot_memory: list[dict] = Field(default_factory=list)
    chapter_analyses: list[dict] = Field(default_factory=list)
    generation_config: Optional[dict] = None
    writing_style_id: Optional[str] = None
    active_skill: Optional[str] = None
    human_feedback: Optional[str] = None


class ChapterAnalyzeRequest(BaseModel):
    """Request: analyze a chapter."""
    project_id: str
    current_chapter_index: int = 0
    chapters: list[dict] = Field(default_factory=list)
    characters: list[dict] = Field(default_factory=list)
    world_setting: dict = Field(default_factory=dict)
    chapter_analyses: list[dict] = Field(default_factory=list)
    foreshadows: list[dict] = Field(default_factory=list)
    generation_config: Optional[dict] = None


class ChapterPolishRequest(BaseModel):
    """Request: polish chapter prose."""
    content: str = Field(..., description="章节内容")
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class ChapterRewriteRequest(BaseModel):
    """Request: rewrite chapter."""
    content: str = Field(..., description="章节内容")
    feedback: str = Field("请改善", description="重写反馈/指令")
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None


class PartialRegenerateRequest(BaseModel):
    """Request: partial regenerate selected text."""
    selected_text: str = Field(..., min_length=1, description="选中的文本")
    strategy: str = Field("similar", description="重写策略: similar/expand/condense/custom")
    custom_instruction: Optional[str] = Field(None, description="自定义指令(strategy=custom时)")
    provider: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
