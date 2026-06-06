"""Projects API (api.md §3, API-1/2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from cardenio.api.deps import get_artifact_store
from cardenio.domain.models.project import ProjectMeta
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects")


@router.post("", status_code=201)
async def create_project(
    meta: ProjectMeta,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-1: Create a new adaptation project."""
    project_id = await store.create_project(meta.model_dump(mode="json"))
    project = await store.get_project(project_id)
    return project


@router.get("")
async def list_projects(
    limit: int = 20,
    cursor: str | None = None,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-2: List projects with cursor pagination."""
    projects = await store.list_projects(limit=limit, cursor=cursor)
    return {"items": projects, "next_cursor": None}


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-2: Get project details including state and gate status."""
    proj = await store.get_project(project_id)
    if proj is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.patch("/{project_id}")
async def update_project(project_id: str, meta: ProjectMeta) -> dict:
    """API-2: Update project metadata (title, languages, direction)."""
    raise NotImplementedError("Project update not yet implemented")


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    """API-2: Soft-delete project and cascade artifacts."""
    raise NotImplementedError("Project deletion not yet implemented")
