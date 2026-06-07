"""Artifact version recovery API (NFR-6, M8-T4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from cardenio.api.deps import get_artifact_store
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/artifacts")

RECOVERABLE_ARTIFACT_TYPES = {
    "understanding",
    "characters",
    "intent",
    "outline",
    "screenplay",
    "report",
    "settings",
}


@router.get("/{artifact_type}/versions")
async def list_artifact_versions(
    project_id: str,
    artifact_type: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """List saved versions for a recoverable project artifact."""
    _validate_artifact_type(artifact_type)
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    versions = await store.list_artifact_versions(project_id, artifact_type)
    return {
        "items": [
            {
                "type": artifact.type,
                "state": artifact.state.value,
                "version": artifact.version,
                "parent_version": artifact.parent_version,
                "updated_at": artifact.updated_at,
                "needs_recompute": artifact.needs_recompute,
            }
            for artifact in versions
        ],
        "count": len(versions),
    }


@router.get("/{artifact_type}/versions/{version}")
async def get_artifact_version(
    project_id: str,
    artifact_type: str,
    version: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """Recover a specific saved artifact version without mutating latest."""
    _validate_artifact_type(artifact_type)
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact_version(project_id, artifact_type, version)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact version not found")
    return artifact.model_dump(mode="json")


def _validate_artifact_type(artifact_type: str) -> None:
    if artifact_type not in RECOVERABLE_ARTIFACT_TYPES:
        raise HTTPException(status_code=422, detail="Unsupported artifact type")
