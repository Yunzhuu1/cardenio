"""Export API (api.md §12, API-27/28)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/export")


@router.post("", status_code=202)
async def create_export(project_id: str, body: dict) -> dict:
    """API-27: Create an export job (Fountain, DOCX, PDF)."""
    raise NotImplementedError("Export creation not yet implemented")


@router.get("/{export_id}")
async def get_export_status(project_id: str, export_id: str) -> dict:
    """API-28: Get export status and download URL when ready."""
    raise NotImplementedError("Export status not yet implemented")
