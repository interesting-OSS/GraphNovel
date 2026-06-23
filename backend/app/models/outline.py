"""Outline model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Outline(Base):
    __tablename__ = "outlines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    volume: Mapped[int] = mapped_column(Integer, default=1)
    chapter_num: Mapped[int] = mapped_column(Integer, default=1)
    title: Mapped[str] = mapped_column(String(500), default="")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_points: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    mode: Mapped[str] = mapped_column(String(50), default="one-to-one")  # one-to-one / one-to-many
    expansion_strategy: Mapped[str] = mapped_column(String(50), default="balanced")  # balanced/climax/detail
    expansion_plan: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    parent_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("outlines.id", ondelete="SET NULL"), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
