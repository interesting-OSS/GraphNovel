"""Settings and API preset models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, Boolean, Float, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SettingsModel(Base):
    __tablename__ = "settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ai_provider: Mapped[str] = mapped_column(String(50), default="deepseek")
    llm_model: Mapped[str] = mapped_column("ai_model", String(100), default="deepseek-v4-pro")
    ai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_base_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=32000)
    active_preset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    analysis_preset_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    theme: Mapped[str] = mapped_column(String(20), default="system")  # light/dark/system
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class APIPreset(Base):
    __tablename__ = "api_presets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(200), default="")
    provider: Mapped[str] = mapped_column(String(50), default="deepseek")
    llm_model: Mapped[str] = mapped_column("model", String(100), default="deepseek-v4-pro")
    api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=32000)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
