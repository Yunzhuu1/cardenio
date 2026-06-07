"""Report (adaptation tradeoff) API (api.md §11, API-25/26)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.services.report_service import ReportService
from cardenio.gateway.protocol import LlmGateway
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/report")


@router.post(":generate", status_code=202)
async def generate_report(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-25: Generate adaptation tradeoff report (async Job).

    Gate: screenplay must exist.
    Cross-check: report statistics must match screenplay flag counts (FR-10).
    """
    service = ReportService(gateway=gateway, store=store)
    return await service.generate_report(project_id)


@router.get("")
async def get_report(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-26: Get the report artifact envelope."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "report")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return artifact.model_dump(mode="json")
