"""Request ID middleware — adds unique ID to each request for tracing."""
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign a unique request ID to each incoming request.

    Injects the request_id into both the request state and the log record,
    enabling cross-request tracing in logs via the UvicornFormatter.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Inject into log adapter so all logs during this request carry the ID
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            if not getattr(record, "request_id", None):
                record.request_id = request_id
            return record

        logging.setLogRecordFactory(record_factory)
        try:
            response: Response = await call_next(request)
        finally:
            logging.setLogRecordFactory(old_factory)

        response.headers["X-Request-ID"] = request_id
        return response
