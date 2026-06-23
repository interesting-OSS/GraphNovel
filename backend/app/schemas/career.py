"""Career schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class CareerLevel(BaseModel):
    """A level within a career path."""
    name: str = Field(..., description="等级名称")
    index: int = Field(..., description="等级序号")
    description: str = Field("", description="等级描述")
    abilities: list[str] = Field(default_factory=list, description="该等级能力")


class CareerCreate(BaseModel):
    """Request: create a career path."""
    project_id: str = Field(..., description="所属项目ID")
    name: str = Field(..., min_length=1, max_length=200, description="职业名称")
    career_type: str = Field("主要职业", description="职业分类")
    description: str = Field("", description="职业描述")
    levels: list[CareerLevel] = Field(default_factory=list, description="等级体系")


class CareerUpdate(BaseModel):
    """Request: update a career."""
    name: Optional[str] = Field(None, max_length=200)
    career_type: Optional[str] = None
    description: Optional[str] = None
    levels: Optional[list[CareerLevel]] = None


class CareerResponse(BaseModel):
    """Response: career details."""
    id: str
    project_id: str
    name: str
    career_type: str
    description: Optional[str] = None
    levels: Optional[list[dict]] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
