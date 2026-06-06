"""SQLite-backed ArtifactStore and JobStore implementations.

Concrete persistence via SQLAlchemy async sessions + aiosqlite.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.storage.repository import (
    ArtifactRepository,
    JobRepository,
    ProjectRepository,
)
from cardenio.storage.sqlalchemy_models import ArtifactModel


class SqliteArtifactStore:
    """SQLite implementation of ArtifactStore (design.md §5.1)."""

    def __init__(self, session: AsyncSession) -> None:
        self._projects = ProjectRepository(session)
        self._artifacts = ArtifactRepository(session)

    # -- Project ---------------------------------------------------------------

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        proj = await self._projects.get(project_id)
        if proj is None:
            return None
        return {
            "id": proj.id,
            "title": proj.title,
            "ui_language": proj.ui_language,
            "source_language": proj.source_language,
            "output_language": proj.output_language,
            "state": ProjectState(proj.state),
            "adaptation_direction": proj.adaptation_direction,
            "style_fingerprint": proj.style_fingerprint,
        }

    async def create_project(self, meta: dict[str, Any]) -> str:
        proj = await self._projects.create(
            title=meta["title"],
            ui_language=meta.get("ui_language", "zh-CN"),
            source_language=meta.get("source_language", "zh-CN"),
            output_language=meta.get("output_language", "zh-CN"),
            adaptation_direction=meta.get("adaptation_direction"),
        )
        return proj.id

    async def update_project_state(self, project_id: str, state: ProjectState) -> None:
        await self._projects.update_state(project_id, state.value)

    async def list_projects(
        self, *, limit: int = 20, cursor: str | None = None
    ) -> list[dict[str, Any]]:
        projects = await self._projects.list_projects(limit=limit, cursor=cursor)
        return [
            {
                "id": p.id,
                "title": p.title,
                "state": p.state,
                "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            }
            for p in projects
        ]

    # -- Artifact --------------------------------------------------------------

    async def get_artifact(
        self, project_id: str, artifact_type: str
    ) -> ArtifactEnvelope[Any] | None:
        row = await self._artifacts.get_latest(project_id, artifact_type)
        if row is None:
            return None
        return self._row_to_envelope(row)

    async def save_artifact(
        self, project_id: str, artifact: ArtifactEnvelope[Any]
    ) -> ArtifactEnvelope[Any]:
        row = ArtifactModel(
            project_id=project_id,
            type=artifact.type,
            state=artifact.state.value,
            version=artifact.version,
            parent_version=artifact.parent_version,
            etag=artifact.etag,
            needs_recompute=artifact.needs_recompute,
            data=json.dumps(
                artifact.data.model_dump(mode="json")
                if hasattr(artifact.data, "model_dump")
                else artifact.data,
                ensure_ascii=False,
            ),
        )
        await self._artifacts.save(row)
        return self._row_to_envelope(row)

    # -- Paragraph index -------------------------------------------------------

    async def save_paragraphs(
        self,
        project_id: str,
        chapter_id: str,
        paragraphs: list[dict[str, Any]],
    ) -> None:
        """Bulk-insert source paragraphs for a chapter."""
        for p in paragraphs:
            await self._artifacts.save_paragraph(
                project_id=project_id,
                chapter_id=chapter_id,
                paragraph_index=p["index"],
                text=p["text"],
            )

    async def delete_paragraphs(self, project_id: str, chapter_id: str) -> int:
        """Delete all paragraphs for a chapter. Returns count deleted."""
        return await self._artifacts.delete_paragraphs(project_id, chapter_id)

    async def delete_all_paragraphs(self, project_id: str) -> int:
        """Delete all source paragraphs for a project."""
        return await self._artifacts.delete_all_paragraphs(project_id)

    async def get_paragraphs(
        self, project_id: str, chapter_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Get all paragraphs for a project, optionally filtered by chapter."""
        rows = await self._artifacts.get_paragraphs(
            project_id, chapter_id=chapter_id
        )
        return [
            {
                "id": r.id,
                "project_id": r.project_id,
                "chapter_id": r.chapter_id,
                "paragraph_index": r.paragraph_index,
                "text": r.text,
            }
            for r in rows
        ]

    async def list_chapters(self, project_id: str) -> list[dict[str, Any]]:
        """Get all chapters for a project, grouped from paragraph index."""
        rows = await self._artifacts.get_paragraphs(project_id)

        # Group paragraphs by chapter_id
        chapters: dict[str, dict[str, Any]] = {}
        for r in rows:
            cid = r.chapter_id
            if cid not in chapters:
                chapters[cid] = {
                    "id": cid,
                    "title": cid.replace("_", " ").title(),
                    "order": len(chapters) + 1,
                    "char_count": 0,
                    "paragraphs": [],
                }
            chapters[cid]["paragraphs"].append({
                "index": r.paragraph_index,
                "text": r.text,
            })
            chapters[cid]["char_count"] += len(r.text)

        return list(chapters.values())

    @staticmethod
    def _row_to_envelope(row: ArtifactModel) -> ArtifactEnvelope[Any]:
        return ArtifactEnvelope(
            type=row.type,
            state=ArtifactState(row.state),
            version=row.version,
            parent_version=row.parent_version,
            etag=row.etag,
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
            needs_recompute=row.needs_recompute,
            data=json.loads(row.data),
        )


class SqliteJobStore:
    """SQLite implementation of JobStore (api.md §2.4)."""

    def __init__(self, session: AsyncSession) -> None:
        self._jobs = JobRepository(session)

    async def create_job(self, *, project_id: str, kind: str) -> dict[str, Any]:
        job = await self._jobs.create(project_id=project_id, kind=kind)
        return {
            "id": job.id,
            "project_id": job.project_id,
            "kind": job.kind,
            "status": job.status,
            "error": job.error,
        }

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        job = await self._jobs.get(job_id)
        if job is None:
            return None
        return {
            "id": job.id,
            "project_id": job.project_id,
            "kind": job.kind,
            "status": job.status,
            "error": job.error,
        }

    async def update_job_status(
        self, job_id: str, status: str, error: str | None = None
    ) -> None:
        await self._jobs.update_status(job_id, status, error=error)
