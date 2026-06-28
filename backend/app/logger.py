"""Thin re-export shim — delegates to app.logging_config for unified logging.

All functionality now lives in app.logging_config. This module exists purely
for backward compatibility with existing imports from app.logger.
"""
from app.logging_config import (  # noqa: F401
    setup_logging,
    get_logger,
    SENSITIVE_LOG_KEYS,
    _sanitize_for_log,
    ContextVarFilter,
    JsonFormatter,
    ColorFormatter,
)
