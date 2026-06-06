"""Repository pattern implementation for persistence.

Uses SQLAlchemy async sessions.  The repository provides a clean interface
over raw ORM operations, keeping query logic out of the API layer.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from cardenio.storage.sqlalchemy_models import (
    ArtifactModel,
    JobModel,
    ProjectModel,
    SourceParagraphModel,
)


class ProjectRepository:
    """Repository for project CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, project_id: str) -> ProjectModel | None:
        return await self.session.get(ProjectModel, project_id)

    async def create(self, **kwargs: Any) -> ProjectModel:
        project = ProjectModel(**kwargs)
        self.session.add(project)
        await self.session.flush()
        return project

    async def update_state(self, project_id: str, state: str) -> None:
        project = await self.get(project_id)
        if project:
            project.state = state
            await self.session.flush()

    async def list_projects(
        self, *, limit: int = 20, cursor: str | None = None
    ) -> list[ProjectModel]:
        stmt = select(ProjectModel).order_by(ProjectModel.updated_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class ArtifactRepository:
    """Repository for artifact CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_latest(
        self, project_id: str, artifact_type: str
    ) -> ArtifactModel | None:
        stmt = (
            select(ArtifactModel)
            .where(
                ArtifactModel.project_id == project_id,
                ArtifactModel.type == artifact_type,
            )
            .order_by(ArtifactModel.updated_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, artifact: ArtifactModel) -> ArtifactModel:
        self.session.add(artifact)
        await self.session.flush()
        return artifact

    async def save_paragraph(
        self,
        *,
        project_id: str,
        chapter_id: str,
        paragraph_index: int,
        text: str,
    ) -> SourceParagraphModel:
        para = SourceParagraphModel(
            project_id=project_id,
            chapter_id=chapter_id,
            paragraph_index=paragraph_index,
            text=text,
        )
        self.session.add(para)
        await self.session.flush()
        return para

    async def get_paragraphs(
        self, project_id: str, *, chapter_id: str | None = None
    ) -> list[SourceParagraphModel]:
        from sqlalchemy import select

        stmt = select(SourceParagraphModel).where(
            SourceParagraphModel.project_id == project_id
        )
        if chapter_id:
            stmt = stmt.where(SourceParagraphModel.chapter_id == chapter_id)
        stmt = stmt.order_by(SourceParagraphModel.paragraph_index)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_paragraphs(
        self, project_id: str, chapter_id: str
    ) -> int:
        """Delete all paragraphs for a chapter. Returns count deleted."""
        from sqlalchemy import delete

        stmt = (
            delete(SourceParagraphModel)
            .where(SourceParagraphModel.project_id == project_id)
            .where(SourceParagraphModel.chapter_id == chapter_id)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def delete_all_paragraphs(self, project_id: str) -> int:
        """Delete all source paragraphs for a project. Returns count deleted."""
        from sqlalchemy import delete

        stmt = delete(SourceParagraphModel).where(
            SourceParagraphModel.project_id == project_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount


class JobRepository:
    """Repository for job status tracking."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, job_id: str) -> JobModel | None:
        return await self.session.get(JobModel, job_id)

    async def create(self, **kwargs: Any) -> JobModel:
        job = JobModel(**kwargs)
        self.session.add(job)
        await self.session.flush()
        return job

    async def update_status(
        self, job_id: str, status: str, error: str | None = None
    ) -> None:
        job = await self.get(job_id)
        if job:
            job.status = status
            if error:
                job.error = error
            await self.session.flush()
