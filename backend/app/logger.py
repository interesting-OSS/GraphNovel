"""Unified logging module — Uvicorn-style formatting with rotation and sanitization."""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Any, Optional

DEFAULT_LOG_MESSAGE_MAX_CHARS = 2000
DEFAULT_LOG_PREVIEW_MAX_CHARS = 300

SENSITIVE_LOG_KEYS = {
    "api_key", "apikey", "authorization", "auth", "bearer",
    "cookie", "password", "secret", "token", "access_token", "refresh_token",
}


def _truncate_text(text: str, max_chars: Optional[int] = DEFAULT_LOG_PREVIEW_MAX_CHARS) -> str:
    if max_chars is None or max_chars <= 0 or len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}... [truncated, length={len(text)}]"


def safe_preview(value: Any, max_chars: int = DEFAULT_LOG_PREVIEW_MAX_CHARS) -> str:
    if value is None:
        return "None"
    return _truncate_text(str(value), max_chars)


def summarize_log_value(value: Any) -> str:
    """Return a structural summary of a value without dumping content."""
    if value is None:
        return "None"
    if isinstance(value, str):
        return f"str(length={len(value)})"
    if isinstance(value, dict):
        fields = []
        for k, v in list(value.items())[:20]:
            if isinstance(v, str):
                fields.append(f"{k}:str(len={len(v)})")
            elif isinstance(v, (list, tuple, set)):
                fields.append(f"{k}:{type(v).__name__}(len={len(v)})")
            elif isinstance(v, dict):
                fields.append(f"{k}:dict(keys={len(v)})")
            else:
                fields.append(f"{k}:{type(v).__name__}")
        suffix = f", +{len(value) - 20} keys" if len(value) > 20 else ""
        return f"dict(keys={len(value)}, fields=[{', '.join(fields)}{suffix}])"
    if isinstance(value, (list, tuple, set)):
        item_types = sorted({type(i).__name__ for i in value})
        return f"{type(value).__name__}(length={len(value)}, item_types={item_types})"
    return type(value).__name__


def _sanitize_for_log(value: Any, depth: int = 0) -> Any:
    """Recursively sanitize log objects to avoid leaking sensitive fields or full content."""
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
                sanitized[key_str] = summarize_log_value(item)
            else:
                sanitized[key_str] = _sanitize_for_log(item, depth + 1)
        return sanitized

    if isinstance(value, (list, tuple)):
        items = [_sanitize_for_log(i, depth + 1) for i in value[:10]]
        if len(value) > 10:
            items.append(f"... {len(value) - 10} more items")
        return items

    if isinstance(value, str):
        return safe_preview(value)

    return value


class UvicornFormatter(logging.Formatter):
    """Uvicorn-style log formatter with ANSI colors and request-id support."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True, max_message_chars: int = DEFAULT_LOG_MESSAGE_MAX_CHARS):
        super().__init__()
        self.use_colors = use_colors
        self.max_message_chars = max_message_chars

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname

        if self.use_colors and sys.stderr.isatty():
            colored_level = f"{self.COLORS.get(levelname, '')}{levelname}{self.RESET}"
        else:
            colored_level = levelname

        request_id = getattr(record, "request_id", None)
        rid = f" [{request_id}]" if request_id else ""

        timestamp = self.formatTime(record, self.datefmt)
        message = _truncate_text(record.getMessage(), self.max_message_chars)

        return f"{colored_level}:     [{timestamp}] {record.name}{rid} - {message}"


_logging_configured = False


def setup_logging(
    level: str = "INFO",
    log_to_file: bool = False,
    log_file_path: Optional[str] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 30,
    message_max_chars: int = DEFAULT_LOG_MESSAGE_MAX_CHARS,
) -> logging.Logger:
    """Configure the Uvicorn-style logging system.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to write logs to a file
        log_file_path: Path to the log file
        max_bytes: Max bytes per log file before rotation (default 10 MB)
        backup_count: Number of rotated backup files to keep
        message_max_chars: Max characters per log message (default 2000)
    """
    global _logging_configured

    if _logging_configured:
        return logging.getLogger()

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.handlers.clear()

    if message_max_chars <= 0:
        message_max_chars = DEFAULT_LOG_MESSAGE_MAX_CHARS

    # Console handler (with colors)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_formatter = UvicornFormatter(use_colors=True, max_message_chars=message_max_chars)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler (without colors, with rotation)
    if log_to_file and log_file_path:
        log_file = Path(log_file_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = RotatingFileHandler(
            filename=log_file_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_formatter = UvicornFormatter(use_colors=False, max_message_chars=message_max_chars)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        root_logger.info("Log file output enabled: %s", log_file_path)
        root_logger.info(
            "Log rotation: max %.1f MB, %d backups",
            max_bytes / 1024 / 1024, backup_count,
        )

    # Quiet third-party loggers
    _configure_third_party_loggers()

    _logging_configured = True
    return root_logger


def _configure_third_party_loggers():
    """Set third-party library log levels to avoid noise."""
    for name in ("sqlalchemy.engine", "sqlalchemy.pool", "sqlalchemy.dialects", "sqlalchemy.orm"):
        logging.getLogger(name).setLevel(logging.WARNING)
    for name in ("httpx", "httpcore", "openai", "anthropic", "chromadb", "watchfiles"):
        logging.getLogger(name).setLevel(logging.WARNING)
    # Keep AI service and graph logs at INFO for observability
    logging.getLogger("app.services.ai_service").setLevel(logging.INFO)
    logging.getLogger("app.graphs").setLevel(logging.INFO)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for the given module name."""
    return logging.getLogger(name)
