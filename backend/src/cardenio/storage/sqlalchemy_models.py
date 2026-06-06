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
