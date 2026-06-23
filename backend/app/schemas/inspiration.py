"""Inspiration schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class InspirationCreate(BaseModel):
    """Request: create an inspiration entry."""
    project_id: str = Field(..., description="所属项目ID")
    idea: str = Field(..., min_length=1, description="创意点子")
    insp_type: str = Field("情节转折", description="类型")
    genre_tags: list[str] = Field(default_factory=list, description="类型标签")
    impact: str = Field("medium", description="影响力: high/medium/low")
    implementation: str = Field("", description="实现建议")


class InspirationResponse(BaseModel):
    """Response: inspiration details."""
    id: str
    project_id: Optional[str] = None
    idea: str
    insp_type: str
    genre_tags: Optional[list[str]] = None
    impact: str
    implementation: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
