"""Settings schemas."""
from pydantic import BaseModel, Field
from typing import Optional


class SettingsResponse(BaseModel):
    """Response: global settings."""
    ai_provider: str = "openai"
    ai_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 32000
    theme: str = "system"
    openai_api_key_set: bool = False
    anthropic_api_key_set: bool = False
    google_api_key_set: bool = False


class SettingsUpdate(BaseModel):
    """Request: update settings."""
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0, le=2.0)
    max_tokens: Optional[int] = Field(None, ge=100, le=200000)
    theme: Optional[str] = None


class APIPresetCreate(BaseModel):
    """Request: create an API configuration preset."""
    name: str = Field(..., min_length=1, max_length=100, description="预设名称")
    provider: str = Field("openai", description="AI提供商")
    model: str = Field("gpt-4o", description="模型名称")
    api_key: Optional[str] = Field(None, description="API密钥")
    base_url: Optional[str] = Field(None, description="API地址")
    temperature: float = Field(0.7, ge=0, le=2.0)
    max_tokens: int = Field(32000, ge=100, le=200000)
    is_analysis_preset: bool = Field(False, description="是否用于章节分析")


class APIPresetResponse(BaseModel):
    """Response: API preset details."""
    id: str
    name: str
    provider: str
    model: str
    api_key_set: bool = False
    base_url: Optional[str] = None
    temperature: float
    max_tokens: int
    is_analysis_preset: bool
    is_active: bool = False


class ConnectionTestRequest(BaseModel):
    """Request: test AI API connection."""
    provider: str = "openai"
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    """Response: connection test result."""
    success: bool
    preview: Optional[str] = None
    error: Optional[str] = None
    supports_function_calling: Optional[bool] = None
