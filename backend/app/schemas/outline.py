"""Outline schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class OutlineCreate(BaseModel):
    """Request: create an outline entry."""
    project_id: str = Field(..., description="所属项目ID")
    volume: int = Field(1, ge=1, description="卷号")
    chapter_num: int = Field(1, ge=1, description="章序号")
    title: str = Field("新章节", min_length=1, max_length=500, description="章节标题")
    summary: str = Field("", description="章节摘要")
    key_points: str = Field("", description="关键情节要点")
    mode: Literal["one-to-one", "one-to-many"] = Field("one-to-one", description="大纲对应模式")
    expansion_strategy: Literal["balanced", "climax", "detail"] = Field("balanced", description="扩展策略")
    target_words: int = Field(3000, ge=100, description="目标字数")
    parent_id: Optional[str] = Field(None, description="父大纲ID(层级结构)")


class OutlineUpdate(BaseModel):
    """Request: update an outline entry."""
    title: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = None
    key_points: Optional[str] = None
    volume: Optional[int] = Field(None, ge=1)
    chapter_num: Optional[int] = Field(None, ge=1)
    mode: Optional[Literal["one-to-one", "one-to-many"]] = None
    expansion_strategy: Optional[Literal["balanced", "climax", "detail"]] = None
    target_words: Optional[int] = Field(None, ge=100)
    parent_id: Optional[str] = None


class OutlineResponse(BaseModel):
    """Response: outline details."""
    id: str
    project_id: str
    parent_id: Optional[str] = None
    volume: int
    chapter_num: int
    title: str
    summary: Optional[str] = None
    key_points: Optional[str] = None
    target_words: int
    mode: str
    expansion_strategy: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OutlineListResponse(BaseModel):
    """Response: paginated outline list."""
    total: int
    items: list[OutlineResponse]


class OutlineReorderRequest(BaseModel):
    """Request: reorder outlines."""
    items: list[dict] = Field(..., description="[{\"id\": \"...\", \"chapter_num\": 1, \"volume\": 1}]")
