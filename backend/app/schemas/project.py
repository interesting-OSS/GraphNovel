"""Project schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class ProjectCreate(BaseModel):
    """Request: create a project."""
    title: str = Field(..., min_length=1, max_length=500, description="项目标题")
    description: Optional[str] = Field(None, description="一句话简介")
    genre: str = Field("玄幻", description="小说类型")
    target_words: int = Field(100000, ge=1000, description="目标字数")
    narrative_perspective: str = Field("第三人称", description="叙述视角")
    outline_mode: Literal["one-to-one", "one-to-many"] = Field("one-to-one", description="大纲模式")
    writing_style_id: Optional[str] = Field(None, description="写作风格ID")
    world_setting: Optional[dict] = Field(None, description="世界观设定")
    generation_config: Optional[dict] = Field(None, description="AI生成配置")


class ProjectUpdate(BaseModel):
    """Request: update a project."""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = None
    genre: Optional[str] = None
    target_words: Optional[int] = Field(None, ge=1000)
    narrative_perspective: Optional[str] = None
    status: Optional[Literal["planning", "writing", "revising", "completed"]] = None
    total_word_count: Optional[int] = None
    outline_mode: Optional[Literal["one-to-one", "one-to-many"]] = None
    cover_prompt: Optional[str] = None
    cover_url: Optional[str] = None
    writing_style_id: Optional[str] = None
    active_skill: Optional[str] = None
    world_setting: Optional[dict] = None
    generation_config: Optional[dict] = None


class ProjectResponse(BaseModel):
    """Response: project details."""
    id: str
    title: str
    description: Optional[str] = None
    genre: str
    target_words: int
    narrative_perspective: str
    status: str
    total_word_count: int
    outline_mode: str
    cover_prompt: Optional[str] = None
    cover_url: Optional[str] = None
    writing_style_id: Optional[str] = None
    active_skill: Optional[str] = None
    world_setting: Optional[dict] = None
    generation_config: Optional[dict] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProjectListResponse(BaseModel):
    """Response: paginated project list."""
    total: int
    items: list[ProjectResponse]
