"""Relationship, Organization, and Career models."""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Float, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Career(Base):
    __tablename__ = "careers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    career_type: Mapped[str] = mapped_column(String(100), default="主要职业")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    levels: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: [{name, description, abilities}]
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    org_type: Mapped[str] = mapped_column(String(100), default="门派")  # 门派/势力/组织/家族
    leader_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("characters.id", ondelete="SET NULL"), nullable=True)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    hierarchy: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    alignment: Mapped[str] = mapped_column(String(20), default="中立")  # 正义/中立/邪恶
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class OrganizationMember(Base):
    __tablename__ = "organization_members"
    __table_args__ = (
        UniqueConstraint("organization_id", "character_id", name="uq_org_member"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"))
    character_id: Mapped[str] = mapped_column(String(36), ForeignKey("characters.id", ondelete="CASCADE"))
    role: Mapped[str | None] = mapped_column(String(200), nullable=True)  # 角色在组织中的职位
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CharacterRelationship(Base):
    __tablename__ = "character_relationships"
    __table_args__ = (
        UniqueConstraint("char_a_id", "char_b_id", name="uq_char_relationship"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    char_a_id: Mapped[str] = mapped_column(String(36), ForeignKey("characters.id", ondelete="CASCADE"))
    char_b_id: Mapped[str] = mapped_column(String(36), ForeignKey("characters.id", ondelete="CASCADE"))
    relation_type: Mapped[str] = mapped_column(String(100), default="其他")  # 师徒/敌对/同盟/暗恋/挚友/血亲
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    intimacy: Mapped[float] = mapped_column(Float, default=50.0)  # 0-100
    status: Mapped[str] = mapped_column(String(50), default="正常")  # 正常/疏远/已故/决裂
    source: Mapped[str] = mapped_column(String(50), default="manual")  # manual/ai_generated
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
