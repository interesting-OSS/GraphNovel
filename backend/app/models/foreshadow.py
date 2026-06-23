"""Foreshadow model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Foreshadow(Base):
    __tablename__ = "foreshadows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending/set/resolved/abandoned
    category: Mapped[str] = mapped_column(String(100), default="情节伏笔")  # 人物伏笔/情节伏笔/世界观伏笔
    set_chapter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    target_chapter_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    resolved_chapter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    remind_deadline: Mapped[int | None] = mapped_column(Integer, nullable=True)  # Should resolve before this chapter index
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
