"""Projects API (api.md §3, API-1/2)."""

from __future__ import annotations

from fastapi import APIRouter

from cardenio.domain.models.project import ProjectMeta

router = APIRouter(prefix="/projects")


@router.post("", status_code=201)
async def create_project(meta: ProjectMeta) -> dict:
    """API-1: Create a new adaptation project."""
    # TODO: implement in M0-T3
    raise NotImplementedError("Project creation not yet implemented")


@router.get("")
async def list_projects(*, limit: int = 20, cursor: str | None = None) -> dict:
    """API-2: List projects with cursor pagination."""
    raise NotImplementedError("Project listing not yet implemented")


@router.get("/{project_id}")
async def get_project(project_id: str) -> dict:
    """API-2: Get project details including state and gate status."""
    raise NotImplementedError("Project detail not yet implemented")


@router.patch("/{project_id}")
async def update_project(project_id: str, meta: ProjectMeta) -> dict:
    """API-2: Update project metadata (title, languages, direction)."""
    raise NotImplementedError("Project update not yet implemented")


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str) -> None:
    """API-2: Soft-delete project and cascade artifacts."""
    raise NotImplementedError("Project deletion not yet implemented")
