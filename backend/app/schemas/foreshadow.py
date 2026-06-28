"""Foreshadow schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class ForeshadowCreate(BaseModel):
    """Request: create a foreshadow entry."""
    project_id: str = Field(..., description="所属项目ID")
    description: str = Field(..., min_length=1, description="伏笔描述")
    category: str = Field("情节伏笔", description="分类: 人物伏笔/情节伏笔/世界观伏笔/能力伏笔/情感伏笔")
    status: Literal["pending", "set", "resolved", "abandoned"] = Field("pending", description="状态")
    set_chapter_id: Optional[str] = Field(None, description="设置章节ID")
    target_chapter: Optional[int] = Field(None, ge=1, description="应在第几章前揭示")
    importance: int = Field(5, ge=1, le=10, description="重要性 1-10")


class ForeshadowUpdate(BaseModel):
    """Request: update a foreshadow entry."""
    description: Optional[str] = None
    category: Optional[str] = None
    status: Optional[Literal["pending", "set", "resolved", "abandoned"]] = None
    set_chapter_id: Optional[str] = None
    target_chapter: Optional[int] = Field(None, ge=1)
    importance: Optional[int] = Field(None, ge=1, le=10)


class ForeshadowResponse(BaseModel):
    """Response: foreshadow details."""
    id: str
    project_id: str
    description: str
    category: str
    status: str
    set_chapter_id: Optional[str] = None
    target_chapter: Optional[int] = None
    importance: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ForeshadowStats(BaseModel):
    """Response: foreshadow statistics."""
    total: int
    by_status: dict = Field(default_factory=dict, description="{pending: N, set: N, resolved: N, abandoned: N}")
    by_category: dict = Field(default_factory=dict, description="{category: count}")
    resolution_rate: float = Field(0.0, description="解决率 (百分比)")
    warnings: list[dict] = Field(default_factory=list, description="到期提醒列表")


class ForeshadowTimeline(BaseModel):
    """Response: foreshadow timeline entries."""
    items: list[dict] = Field(default_factory=list, description="[{\"chapter\": N, \"status\": \"\", \"category\": \"\", \"description\": \"\"}]")
