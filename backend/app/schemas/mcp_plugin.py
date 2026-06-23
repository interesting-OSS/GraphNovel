"""MCP Plugin schemas."""
from pydantic import BaseModel, Field
from typing import Optional, Literal


class MCPServerCreate(BaseModel):
    """Request: register a new MCP server."""
    name: str = Field(..., min_length=1, max_length=200, description="插件名称")
    description: Optional[str] = Field(None, description="插件描述")
    transport: Literal["http", "streamable_http", "sse"] = Field("http", description="传输方式")
    url: str = Field(..., min_length=1, max_length=2000, description="服务器 URL")
    enabled: bool = Field(True, description="是否启用")
    config: Optional[dict] = Field(None, description="额外配置")


class MCPServerUpdate(BaseModel):
    """Request: update an existing MCP server."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    transport: Optional[Literal["http", "streamable_http", "sse"]] = None
    url: Optional[str] = Field(None, min_length=1, max_length=2000)
    enabled: Optional[bool] = None
    config: Optional[dict] = None


class MCPServerResponse(BaseModel):
    """Response: MCP server info."""
    id: str
    name: str
    description: Optional[str] = None
    transport: str
    url: str
    enabled: bool
    config: Optional[dict] = None
