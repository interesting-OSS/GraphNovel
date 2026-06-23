"""Chapter model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    outline_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("outlines.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str] = mapped_column(String(500), default="")
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0)
    chapter_index: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft/polished/final
    writing_style_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    model_override: Mapped[str | None] = mapped_column(String(100), nullable=True)
    skill_override: Mapped[str | None] = mapped_column(String(100), nullable=True)
    narrative_perspective_override: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expansion_plan: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    continuation_mode: Mapped[str] = mapped_column(String(50), default="auto")  # auto/new/continue
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
