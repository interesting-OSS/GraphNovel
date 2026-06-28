"""Structured logging configuration with contextvars-based request ID injection.

Provides:
  - ContextVarFilter: injects request_id from contextvars into every log record
  - JSON formatter for production, color formatter for development
  - Sensitive field redaction
"""
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

from app.middleware.request_id import request_id_var

# ── Sensitive key redaction ────────────────────────────────────────────────

SENSITIVE_LOG_KEYS = {
    "api_key", "apikey", "authorization", "auth", "bearer",
    "cookie", "password", "secret", "token", "access_token", "refresh_token",
}


def _sanitize_for_log(value: Any, depth: int = 0) -> Any:
    """Recursively sanitize log objects to avoid leaking secrets or full content."""
    if depth > 4:
        return f"<{type(value).__name__}>"
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            key_str = str(key)
            lower = key_str.lower()
            if any(sk in lower for sk in SENSITIVE_LOG_KEYS):
                sanitized[key_str] = "***REDACTED***"
            elif lower in {"content", "prompt", "system_prompt", "chapter_content", "messages", "arguments"}:
                sanitized[key_str] = f"str(length={len(str(item))})"
            else:
                sanitized[key_str] = _sanitize_for_log(item, depth + 1)
        return sanitized
    if isinstance(value, (list, tuple)):
        return [_sanitize_for_log(i, depth + 1) for i in value[:10]]
    if isinstance(value, str):
        return value[:300] + ("..." if len(value) > 300 else "")
    return value


# ── Filters ─────────────────────────────────────────────────────────────────

class ContextVarFilter(logging.Filter):
    """Inject request_id from contextvars into every log record.

    Unlike the old setLogRecordFactory approach, this has NO race condition:
    each async task gets its own contextvars copy.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            record.request_id = request_id_var.get()
        except (LookupError, RuntimeError):
            record.request_id = "-"
        return True


# ── Formatters ──────────────────────────────────────────────────────────────

class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter for production."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])

        # Include extra fields from sanitized record args
        if record.args and isinstance(record.args, dict):
            log_entry["extra"] = _sanitize_for_log(record.args)

        return json.dumps(log_entry, ensure_ascii=False, default=str)


class ColorFormatter(logging.Formatter):
    """Uvicorn-style colored formatter for development."""

    COLORS = {
        "DEBUG": "\033[36m", "INFO": "\033[32m", "WARNING": "\033[33m",
        "ERROR": "\033[31m", "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def __init__(self, max_message_chars: int = 2000, use_colors: bool = True):
        super().__init__()
        self.max_message_chars = max_message_chars
        self.use_colors = use_colors

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = self.COLORS.get(levelname, "")
        if color and not self.use_colors:
            color = ""

        colored_level = f"{color}{levelname}{self.RESET}" if color else levelname
        request_id = getattr(record, "request_id", None)
        rid = f" [{request_id}]" if request_id else ""
        timestamp = self.formatTime(record, self.datefmt)
        message = record.getMessage()
        if len(message) > self.max_message_chars:
            message = message[:self.max_message_chars] + "... [truncated]"

        return f"{colored_level}:     [{timestamp}] {record.name}{rid} - {message}"


# ── Setup ───────────────────────────────────────────────────────────────────

_logging_configured = False


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = True,
    log_file_path: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 30,
) -> logging.Logger:
    """Configure structured logging for the entire application.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Enable rotating file handler
        log_file_path: Path to log file
        max_bytes: Max bytes per log file before rotation
        backup_count: Number of rotated backups to keep
    """
    global _logging_configured
    if _logging_configured:
        return logging.getLogger()

    is_production = os.getenv("APP_ENV") == "production"

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper()))
    root.handlers.clear()

    contextvar_filter = ContextVarFilter()

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(getattr(logging, level.upper()))
    if is_production:
        console.setFormatter(JsonFormatter())
    else:
        fmt = ColorFormatter(use_colors=True)
        console.setFormatter(fmt)
    console.addFilter(contextvar_filter)
    root.addHandler(console)

    # File handler (always JSON for machine readability)
    if log_to_file and log_file_path:
        from pathlib import Path
        Path(log_file_path).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(JsonFormatter())
        file_handler.addFilter(contextvar_filter)
        root.addHandler(file_handler)

    # Quiet third-party loggers
    for name in ("sqlalchemy.engine", "sqlalchemy.pool", "sqlalchemy.dialects", "sqlalchemy.orm"):
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in ("httpx", "httpcore", "openai", "anthropic", "chromadb", "watchfiles"):
        logging.getLogger(name).setLevel(logging.WARNING)
    logging.getLogger("app.services.ai_service").setLevel(logging.INFO)
    logging.getLogger("app.graphs").setLevel(logging.INFO)

    _logging_configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name."""
    return logging.getLogger(name)
