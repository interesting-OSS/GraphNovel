"""MCP Plugin model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, Boolean, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MCPPlugin(Base):
    __tablename__ = "mcp_plugins"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plugin_name: Mapped[str] = mapped_column("name", String(200), default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    transport: Mapped[str] = mapped_column(String(50), default="streamable_http")  # streamable_http / sse
    url: Mapped[str] = mapped_column(String(2000), default="")
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON

    # Runtime status (synced by status_sync.py background worker)
    mcp_status: Mapped[str] = mapped_column(String(50), default="active")  # active / degraded / error
    mcp_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_checked: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
