"""Inspiration model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Inspiration(Base):
    __tablename__ = "inspirations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    idea: Mapped[str] = mapped_column(Text, default="")
    genre_tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    status: Mapped[str] = mapped_column(String(50), default="draft")  # draft/saved/converted_to_project
    project_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)  # If converted
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
