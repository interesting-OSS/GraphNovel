"""Writing style schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class WritingStyleCreate(BaseModel):
    """Request: create a writing style."""
    name: str = Field(..., min_length=1, max_length=200, description="风格名称")
    description: str = Field("", description="风格描述")
    content: str = Field("", description="风格提示词模板")
    is_preset: bool = Field(False, description="是否内置风格")


class WritingStyleResponse(BaseModel):
    """Response: writing style details."""
    id: str
    project_id: Optional[str] = None
    name: str
    description: Optional[str] = None
    content: Optional[str] = None
    is_preset: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
