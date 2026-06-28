"""Unified error types for GraphNovel.

All application-level exceptions should extend AppError so the global
exception handler can produce consistent JSON error responses.
"""
from typing import Optional


class AppError(Exception):
    """Base application error with HTTP status code."""

    def __init__(self, code: int, message: str, detail: Optional[str] = None):
        self.code = code
        self.message = message
        self.detail = detail
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found (404)."""

    def __init__(self, resource: str, resource_id: str):
        super().__init__(
            code=404,
            message=f"{resource} not found",
            detail=f"{resource} id={resource_id}",
        )


class AIServiceError(AppError):
    """AI provider unavailable or returned an error (502)."""

    def __init__(self, provider: str, detail: Optional[str] = None):
        super().__init__(
            code=502,
            message=f"AI service {provider} unavailable",
            detail=detail,
        )


class ValidationError(AppError):
    """Request validation failed (422)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(code=422, message=message, detail=detail)


class ConflictError(AppError):
    """Resource conflict (409)."""

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(code=409, message=message, detail=detail)


class TaskError(AppError):
    """Background task error (500)."""

    def __init__(self, task_id: str, detail: Optional[str] = None):
        super().__init__(
            code=500,
            message=f"Task {task_id} failed",
            detail=detail,
        )
