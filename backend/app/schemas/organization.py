"""Organization schemas."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class OrganizationCreate(BaseModel):
    """Request: create an organization."""
    project_id: str = Field(..., description="所属项目ID")
    name: str = Field(..., min_length=1, max_length=200, description="组织名称")
    org_type: str = Field("门派", description="组织类型")
    description: str = Field("", description="组织描述")
    goal: str = Field("", description="组织目标")
    hierarchy: Optional[str] = Field(None, description="层级结构(JSON)")
    leader_id: Optional[str] = Field(None, description="首领角色ID")
    alignment: str = Field("中立", description="立场: 正义/中立/邪恶")


class OrganizationUpdate(BaseModel):
    """Request: update an organization."""
    name: Optional[str] = Field(None, max_length=200)
    org_type: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[str] = None
    hierarchy: Optional[str] = None
    leader_id: Optional[str] = None
    alignment: Optional[str] = None


class OrganizationResponse(BaseModel):
    """Response: organization details."""
    id: str
    project_id: str
    name: str
    org_type: str
    description: Optional[str] = None
    goal: Optional[str] = None
    hierarchy: Optional[str] = None
    leader_id: Optional[str] = None
    alignment: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
