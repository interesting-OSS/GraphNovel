"""Pydantic schemas for LangNovel Studio API.

All request/response validation and serialization models.
"""
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
from app.schemas.chapter import ChapterCreate, ChapterUpdate, ChapterResponse, ChapterListResponse
from app.schemas.character import CharacterCreate, CharacterUpdate, CharacterResponse, CharacterListResponse
from app.schemas.outline import OutlineCreate, OutlineUpdate, OutlineResponse, OutlineListResponse
from app.schemas.relationship import RelationshipCreate, RelationshipUpdate, RelationshipResponse
from app.schemas.organization import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from app.schemas.career import CareerCreate, CareerUpdate, CareerResponse
from app.schemas.foreshadow import ForeshadowCreate, ForeshadowUpdate, ForeshadowResponse, ForeshadowStats
from app.schemas.memory import MemoryResponse, AnalysisResponse, MemorySearchResult
from app.schemas.settings import SettingsResponse, SettingsUpdate, APIPresetCreate, APIPresetResponse
from app.schemas.writing_style import WritingStyleCreate, WritingStyleResponse
from app.schemas.inspiration import InspirationCreate, InspirationResponse
from app.schemas.common import PaginatedResponse, ErrorResponse, SuccessResponse
from app.schemas.mcp_plugin import MCPServerCreate, MCPServerUpdate, MCPServerResponse

__all__ = [
    "ProjectCreate", "ProjectUpdate", "ProjectResponse", "ProjectListResponse",
    "ChapterCreate", "ChapterUpdate", "ChapterResponse", "ChapterListResponse",
    "CharacterCreate", "CharacterUpdate", "CharacterResponse", "CharacterListResponse",
    "OutlineCreate", "OutlineUpdate", "OutlineResponse", "OutlineListResponse",
    "RelationshipCreate", "RelationshipUpdate", "RelationshipResponse",
    "OrganizationCreate", "OrganizationUpdate", "OrganizationResponse",
    "CareerCreate", "CareerUpdate", "CareerResponse",
    "ForeshadowCreate", "ForeshadowUpdate", "ForeshadowResponse", "ForeshadowStats",
    "MemoryResponse", "AnalysisResponse", "MemorySearchResult",
    "SettingsResponse", "SettingsUpdate", "APIPresetCreate", "APIPresetResponse",
    "WritingStyleCreate", "WritingStyleResponse",
    "InspirationCreate", "InspirationResponse",
    "PaginatedResponse", "ErrorResponse", "SuccessResponse",
    "MCPServerCreate", "MCPServerUpdate", "MCPServerResponse",
]
