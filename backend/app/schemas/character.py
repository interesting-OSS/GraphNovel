"""Character schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class CharacterCreate(BaseModel):
    """Request: create a character."""
    project_id: str = Field(..., description="所属项目ID")
    name: str = Field("新角色", min_length=1, max_length=100, description="角色名")
    gender: str = Field("男", description="性别")
    age: int = Field(20, ge=0, le=100000, description="年龄")
    role_type: str = Field("supporting", description="角色类型: protagonist/supporting/antagonist")
    appearance: str = Field("", description="外貌描述")
    personality: str = Field("", description="性格描述")
    background: str = Field("", description="背景故事")
    goals: str = Field("", description="目标")
    secrets: str = Field("", description="秘密")
    mental_state: str = Field("正常", description="心理状态")
    power_level: str = Field("", description="战力/等级")
    career_id: Optional[str] = Field(None, description="职业ID")
    org_id: Optional[str] = Field(None, description="组织ID")
    location: str = Field("", description="当前位置")
    motto: str = Field("", description="口头禅/信条")
    color: str = Field("#4ECDC4", description="UI显示颜色")
    avatar_url: Optional[str] = Field(None, description="头像URL")


class CharacterUpdate(BaseModel):
    """Request: update a character."""
    name: Optional[str] = Field(None, max_length=100)
    gender: Optional[str] = None
    age: Optional[int] = Field(None, ge=0, le=100000)
    role_type: Optional[str] = None
    appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    goals: Optional[str] = None
    secrets: Optional[str] = None
    mental_state: Optional[str] = None
    power_level: Optional[str] = None
    career_id: Optional[str] = None
    org_id: Optional[str] = None
    location: Optional[str] = None
    motto: Optional[str] = None
    color: Optional[str] = None
    avatar_url: Optional[str] = None


class CharacterResponse(BaseModel):
    """Response: character details."""
    id: str
    project_id: str
    name: str
    gender: str
    age: int
    role_type: str
    appearance: Optional[str] = None
    personality: Optional[str] = None
    background: Optional[str] = None
    goals: Optional[str] = None
    secrets: Optional[str] = None
    mental_state: Optional[str] = None
    power_level: Optional[str] = None
    career_id: Optional[str] = None
    org_id: Optional[str] = None
    location: Optional[str] = None
    motto: Optional[str] = None
    color: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CharacterListResponse(BaseModel):
    """Response: paginated character list."""
    total: int
    items: list[CharacterResponse]
