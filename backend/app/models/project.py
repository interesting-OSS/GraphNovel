"""Project model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title: Mapped[str] = mapped_column(String(500), default="未命名项目")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    genre: Mapped[str] = mapped_column(String(100), default="玄幻")
    target_words: Mapped[int] = mapped_column(Integer, default=100000)
    narrative_perspective: Mapped[str] = mapped_column(String(50), default="第三人称")
    status: Mapped[str] = mapped_column(String(50), default="planning")  # planning/writing/revising/completed
    total_word_count: Mapped[int] = mapped_column(Integer, default=0)
    outline_mode: Mapped[str] = mapped_column(String(50), default="one-to-one")  # one-to-one / one-to-many
    world_setting: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    cover_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    writing_style_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    prompt_template_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    active_skill: Mapped[str | None] = mapped_column(String(100), nullable=True)
    generation_config: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: {provider, model, api_key, ...}
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
