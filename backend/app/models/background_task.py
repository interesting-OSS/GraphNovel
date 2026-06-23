"""Background task model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, Float, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    task_type: Mapped[str] = mapped_column(String(100), default="")  # batch_generate/batch_analyze/batch_polish/book_import
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending/running/paused/completed/failed/cancelled
    progress: Mapped[float] = mapped_column(Float, default=0.0)  # 0-100
    config: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON config
    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON result
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    can_pause: Mapped[bool] = mapped_column(Boolean, default=True)
    can_cancel: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
