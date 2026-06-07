"""SQLAlchemy ORM models for persistence (design.md §5.1).

Projects, artifacts, source paragraphs, and jobs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class UserModel(Base):
    """Application users for first-party login."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"usr_{uuid4().hex[:8]}"
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=func.now()
    )


class AuthSessionModel(Base):
    """Server-side session record backing opaque bearer tokens."""

    __tablename__ = "auth_sessions"
    __table_args__ = (UniqueConstraint("token_hash"),)

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"sess_{uuid4().hex[:8]}"
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=func.now()
    )


class ProjectModel(Base):
    """Projects table — one project per adaptation."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"prj_{uuid4().hex[:8]}"
    )
    title: Mapped[str] = mapped_column(String(500))
    ui_language: Mapped[str] = mapped_column(String(10), default="zh-CN")
    source_language: Mapped[str] = mapped_column(String(10), default="zh-CN")
    output_language: Mapped[str] = mapped_column(String(10), default="zh-CN")
    state: Mapped[str] = mapped_column(String(50), default="empty")
    adaptation_direction: Mapped[str | None] = mapped_column(String(50), nullable=True)
    style_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class ArtifactModel(Base):
    """Artifacts table — versioned, typed artifacts per project."""

    __tablename__ = "artifacts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: uuid4().hex
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    type: Mapped[str] = mapped_column(String(50))  # understanding, characters, etc.
    state: Mapped[str] = mapped_column(String(50), default="draft")
    version: Mapped[str] = mapped_column(String(50))
    parent_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    etag: Mapped[str | None] = mapped_column(String(100), nullable=True)
    needs_recompute: Mapped[bool] = mapped_column(default=False)
    data: Mapped[str] = mapped_column(Text)  # JSON serialized artifact data
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=func.now()
    )


class SourceParagraphModel(Base):
    """Source paragraphs — the root of traceability (P4)."""

    __tablename__ = "source_paragraphs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    chapter_id: Mapped[str] = mapped_column(String(36), index=True)
    paragraph_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)


class JobModel(Base):
    """Async job tracking (api.md §2.4)."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: f"job_{uuid4().hex[:8]}"
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), index=True)
    kind: Mapped[str] = mapped_column(String(50))  # understand, profile, outline, etc.
    status: Mapped[str] = mapped_column(String(20), default="queued")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=func.now()
    )
