"""Understanding (work analysis) API (api.md section 5, API-7/8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.models.understanding import UnderstandingData
from cardenio.domain.services.analysis_service import AnalysisService
from cardenio.gateway.protocol import LlmGateway
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/understanding")


@router.post(":generate", status_code=202)
async def generate_understanding(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-7: Generate understanding artifact."""
    service = AnalysisService(gateway=gateway, store=store)
    return await service.generate_understanding(project_id)


@router.get("")
async def get_understanding(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-8: Get understanding artifact envelope."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "understanding")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Understanding not found")
    return artifact.model_dump(mode="json")


@router.put("")
async def update_understanding(
    project_id: str,
    body: UnderstandingData,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-8: Edit understanding artifact; edited draft becomes the source of truth."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "understanding")
    envelope = ArtifactEnvelope[UnderstandingData](
        type="understanding",
        state=ArtifactState.DRAFT,
        parent_version=previous.version if previous else None,
        data=body,
    )
    saved = await store.save_artifact(project_id, envelope)
    await store.update_project_style_fingerprint(project_id, body.style_fingerprint)
    return saved.model_dump(mode="json")


@router.post(":confirm")
async def confirm_understanding(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-8: Confirm understanding so downstream P1 gates can pass."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "understanding")
    if previous is None:
        raise HTTPException(status_code=404, detail="Understanding not found")

    data = UnderstandingData.model_validate(previous.data)
    envelope = ArtifactEnvelope[UnderstandingData](
        type="understanding",
        state=ArtifactState.CONFIRMED,
        parent_version=previous.version,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    await store.update_project_style_fingerprint(project_id, data.style_fingerprint)
    if project["state"] == ProjectState.IMPORTED:
        await store.update_project_state(project_id, ProjectState.UNDERSTOOD)
    return saved.model_dump(mode="json")
