"""Repository pattern implementation for persistence.

Uses SQLAlchemy async sessions.  The repository provides a clean interface
over raw ORM operations, keeping query logic out of the API layer.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from cardenio.storage.sqlalchemy_models import (
    ArtifactModel,
    AuthSessionModel,
    JobModel,
    ProjectModel,
    SourceParagraphModel,
    UserModel,
)


class UserRepository:
    """Repository for user account lookup and creation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, user_id: str) -> UserModel | None:
        return await self.session.get(UserModel, user_id)

    async def get_by_email(self, email: str) -> UserModel | None:
        stmt = select(UserModel).where(UserModel.email == email).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str | None,
    ) -> UserModel:
        user = UserModel(
            email=email,
            password_hash=password_hash,
            display_name=display_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user


class AuthSessionRepository:
    """Repository for bearer-token sessions."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> AuthSessionModel:
        session = AuthSessionModel(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_active_by_token_hash(
        self,
        token_hash: str,
        *,
        now: datetime,
    ) -> AuthSessionModel | None:
        stmt = (
            select(AuthSessionModel)
            .where(
                AuthSessionModel.token_hash == token_hash,
                AuthSessionModel.revoked_at.is_(None),
                AuthSessionModel.expires_at > now,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_by_token_hash(self, token_hash: str, *, now: datetime) -> bool:
        session = await self.get_active_by_token_hash(token_hash, now=now)
        if session is None:
            return False
        session.revoked_at = now
        await self.session.flush()
        return True


class ProjectRepository:
    """Repository for project CRUD operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, project_id: str) -> ProjectModel | None:
        project = await self.session.get(ProjectModel, project_id)
        if project is not None and project.deleted_at is not None:
            return None
        return project

    async def get_any(self, project_id: str) -> ProjectModel | None:
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

    async def update_style_fingerprint(
        self, project_id: str, style_fingerprint: str
    ) -> None:
        project = await self.get(project_id)
        if project:
            project.style_fingerprint = style_fingerprint
            await self.session.flush()

    async def update_adaptation_direction(
        self, project_id: str, adaptation_direction: str
    ) -> None:
        project = await self.get(project_id)
        if project:
            project.adaptation_direction = adaptation_direction
            await self.session.flush()

    async def update_meta(self, project_id: str, **kwargs: Any) -> ProjectModel | None:
        project = await self.get(project_id)
        if project is None:
            return None
        for field, value in kwargs.items():
            setattr(project, field, value)
        await self.session.flush()
        return project

    async def soft_delete(self, project_id: str) -> bool:
        project = await self.get(project_id)
        if project is None:
            return False
        project.deleted_at = datetime.now(UTC)
        await self.session.flush()
        return True

    async def list_projects(
        self, *, limit: int = 20, cursor: str | None = None
    ) -> list[ProjectModel]:
        stmt = (
            select(ProjectModel)
            .where(ProjectModel.deleted_at.is_(None))
            .order_by(ProjectModel.updated_at.desc())
            .limit(limit)
        )
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

    async def get_version(
        self, project_id: str, artifact_type: str, version: str
    ) -> ArtifactModel | None:
        stmt = (
            select(ArtifactModel)
            .where(
                ArtifactModel.project_id == project_id,
                ArtifactModel.type == artifact_type,
                ArtifactModel.version == version,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_versions(
        self, project_id: str, artifact_type: str
    ) -> list[ArtifactModel]:
        stmt = (
            select(ArtifactModel)
            .where(
                ArtifactModel.project_id == project_id,
                ArtifactModel.type == artifact_type,
            )
            .order_by(ArtifactModel.updated_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

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
        stmt = delete(SourceParagraphModel).where(
            SourceParagraphModel.project_id == project_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount

    async def delete_all_artifacts(self, project_id: str) -> int:
        """Delete all artifacts for a project. Returns count deleted."""
        stmt = delete(ArtifactModel).where(ArtifactModel.project_id == project_id)
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

    async def delete_project_jobs(self, project_id: str) -> int:
        stmt = delete(JobModel).where(JobModel.project_id == project_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount
