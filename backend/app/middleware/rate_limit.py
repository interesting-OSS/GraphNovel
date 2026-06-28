"""In-memory rate limiting middleware.

Limits requests per client IP to protect AI service quota and database
connections from abuse. Excludes health check endpoints.
"""
import time
from collections import defaultdict
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.schemas.response import ApiResponse


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window rate limiter per client IP."""

    EXCLUDED_PATHS = {"/health", "/api/health", "/api/docs", "/api/redoc", "/api/openapi.json"}

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.rpm = requests_per_minute
        self._windows: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip health check and docs endpoints
        if request.url.path in self.EXCLUDED_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        cutoff = now - 60

        # Clean expired entries
        window = self._windows[client_ip]
        self._windows[client_ip] = [t for t in window if t > cutoff]

        if len(self._windows[client_ip]) >= self.rpm:
            return JSONResponse(
                status_code=429,
                content=ApiResponse.error(429, "Rate limit exceeded. Try again later.").model_dump(),
            )

        self._windows[client_ip].append(now)

        # Periodic cleanup of stale clients (every ~100 requests)
        if len(self._windows) > 1000:
            stale = [ip for ip, times in self._windows.items() if not times]
            for ip in stale:
                del self._windows[ip]

        return await call_next(request)
