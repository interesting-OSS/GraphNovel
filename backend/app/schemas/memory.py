"""Memory / chapter analysis schemas."""
from pydantic import BaseModel, Field
from typing import Optional


class MemoryResponse(BaseModel):
    """Response: a single memory record."""
    id: str
    project_id: str
    chapter_index: Optional[int] = None
    summary: Optional[str] = None
    memory_layer: Optional[str] = None
    memory_type: Optional[str] = None


class AnalysisResponse(BaseModel):
    """Response: chapter analysis details."""
    id: Optional[str] = None
    chapter_index: Optional[int] = None
    plot_points: list[dict] = Field(default_factory=list)
    conflict_info: dict = Field(default_factory=dict)
    emotional_arc: dict = Field(default_factory=dict)
    pacing_analysis: dict = Field(default_factory=dict)
    quality_score: Optional[float] = None
    engagement_score: Optional[float] = None
    coherence_score: Optional[float] = None
    suggestions: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    report: Optional[str] = None


class MemorySearchResult(BaseModel):
    """Response: a vector search result."""
    content: str = Field("", description="匹配的文本片段")
    metadata: dict = Field(default_factory=dict, description="元数据")
    score: float = Field(1.0, description="相似度分数")
