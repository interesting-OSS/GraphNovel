"""Request ID middleware — contextvars-based, no global state mutation.

Uses contextvars.ContextVar to isolate request IDs per async task,
eliminating the race condition in the old logging.setLogRecordFactory() approach.
"""
import uuid
from contextvars import ContextVar
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# ContextVar — each async task gets its own copy, no cross-request interference
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def get_request_id() -> str:
    """Get the current request's ID. Safe to call from any depth."""
    return request_id_var.get()


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a unique request ID to each incoming request.

    Uses contextvars so concurrent requests don't interfere with each other.
    Injects the ID into:
      - request.state.request_id (for app code)
      - response header X-Request-ID (for clients)
      - contextvars (for log filters to pick up)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id

        token = request_id_var.set(request_id)
        try:
            response: Response = await call_next(request)
        finally:
            request_id_var.reset(token)

        response.headers["X-Request-ID"] = request_id
        return response
