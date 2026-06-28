"""Unified API response models.

All endpoints should wrap their return values in ApiResponse for consistent
client-side parsing. Paginated endpoints use PaginatedResponse.
"""
from typing import Generic, TypeVar, Optional
from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    Example:
        @router.get("/projects")
        async def list_projects() -> ApiResponse[list[ProjectOut]]:
            ...
            return ApiResponse.success(projects)
    """

    code: int = 200
    message: str = "success"
    data: Optional[T] = None
    request_id: Optional[str] = None

    @classmethod
    def success(cls, data: T = None, message: str = "success") -> "ApiResponse[T]":
        return cls(code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int, message: str, request_id: Optional[str] = None) -> "ApiResponse":
        return cls(code=code, message=message, data=None, request_id=request_id)

    model_config = {"from_attributes": True}


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated list response."""

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_items(
        cls, items: list[T], total: int, page: int, page_size: int
    ) -> "PaginatedResponse[T]":
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
