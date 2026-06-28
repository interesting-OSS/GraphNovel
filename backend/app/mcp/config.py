"""MCP module configuration — immutable constants.

All tunable parameters for connection management, health checks,
tool caching, retry logic, and timeouts live here.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class MCPConfig:
    """Immutable MCP configuration. Tune via environment or code."""

    # Connection pool
    max_clients: int = 1000
    client_ttl_seconds: int = 3600       # 1 hour
    idle_timeout_seconds: int = 1800     # 30 minutes

    # Health check
    health_check_interval: int = 60       # seconds
    error_rate_critical: float = 0.70     # session marked ERROR
    error_rate_warning: float = 0.40      # session marked DEGRADED

    # Cleanup
    cleanup_interval: int = 300           # 5 minutes

    # Tool cache
    tool_cache_ttl: int = 600             # 10 minutes

    # Retry
    max_retries: int = 3
    retry_base_delay: float = 1.0         # seconds
    retry_max_delay: float = 10.0         # seconds

    # Timeouts
    default_timeout: float = 60.0         # seconds
    tool_call_timeout: float = 120.0
    connect_timeout: float = 30.0


# Default global config — override per-deployment
mcp_config = MCPConfig()
