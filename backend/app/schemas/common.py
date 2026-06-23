"""Common Pydantic schemas shared across all API modules."""
from pydantic import BaseModel, Field
from typing import TypeVar, Generic, Optional

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper."""
    total: int = Field(0, description="Total number of items")
    items: list[T] = Field(default_factory=list, description="List of items")


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Error message")
    code: Optional[str] = Field(None, description="Error code")


class SuccessResponse(BaseModel):
    """Standard success response."""
    message: str = Field("ok", description="Success message")
    id: Optional[str] = Field(None, description="Created/updated resource ID")


class DeletedResponse(BaseModel):
    """Standard delete confirmation."""
    deleted: bool = Field(True, description="Whether deletion succeeded")
