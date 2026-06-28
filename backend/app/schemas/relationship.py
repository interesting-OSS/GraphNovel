"""Character relationship schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class RelationshipCreate(BaseModel):
    """Request: create a character relationship."""
    project_id: str = Field(..., description="所属项目ID")
    char_a_id: str = Field(..., description="角色A ID")
    char_b_id: str = Field(..., description="角色B ID")
    relation_type: str = Field("其他", description="关系类型")
    description: str = Field("", description="关系描述")
    intimacy: int = Field(50, ge=0, le=100, description="亲密度 0-100")
    status: str = Field("正常", description="关系状态: 正常/疏远/已故")
    source: str = Field("手动创建", description="来源: 手动创建/AI生成")


class RelationshipUpdate(BaseModel):
    """Request: update a relationship."""
    char_a_id: Optional[str] = None
    char_b_id: Optional[str] = None
    relation_type: Optional[str] = None
    description: Optional[str] = None
    intimacy: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[str] = None


class RelationshipResponse(BaseModel):
    """Response: relationship details."""
    id: str
    project_id: str
    char_a_id: str
    char_b_id: str
    relation_type: str
    description: Optional[str] = None
    intimacy: int
    status: str
    source: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
