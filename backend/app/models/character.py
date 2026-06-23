"""Character model."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="未命名角色")
    gender: Mapped[str] = mapped_column(String(20), default="男")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    role_type: Mapped[str] = mapped_column(String(50), default="supporting")  # protagonist/antagonist/supporting
    appearance: Mapped[str | None] = mapped_column(Text, nullable=True)
    personality: Mapped[str | None] = mapped_column(Text, nullable=True)
    background: Mapped[str | None] = mapped_column(Text, nullable=True)
    goals: Mapped[str | None] = mapped_column(Text, nullable=True)
    secrets: Mapped[str | None] = mapped_column(Text, nullable=True)
    mental_state: Mapped[str | None] = mapped_column(Text, nullable=True)
    career_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("careers.id", ondelete="SET NULL"), nullable=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    power_level: Mapped[str | None] = mapped_column(String(100), nullable=True)
    current_location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    motto: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ui_color: Mapped[str] = mapped_column(String(20), default="#4D8088")
    traits: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
