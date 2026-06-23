"""Story memory and plot analysis models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class StoryMemory(Base):
    __tablename__ = "story_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    memory_type: Mapped[str] = mapped_column(String(50), default="plot")  # plot/character/event/foreshadow
    embedding_id: Mapped[str | None] = mapped_column(String(200), nullable=True)  # ChromaDB embedding ID
    importance: Mapped[float] = mapped_column(Float, default=0.5)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PlotAnalysis(Base):
    __tablename__ = "plot_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    chapter_id: Mapped[str] = mapped_column(String(36), ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    plot_points: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    conflict_info: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    emotional_arc: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    character_arcs: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    pacing_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    engagement_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    coherence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggestions: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    report: Mapped[str | None] = mapped_column(Text, nullable=True)  # Markdown analysis report
    dialogue_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    description_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    narrative_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
