"""Report (adaptation tradeoff) API (api.md §11, API-25/26)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/report")


@router.post(":generate", status_code=202)
async def generate_report(project_id: str) -> dict:
    """API-25: Generate adaptation tradeoff report (async Job).

    Gate: screenplay must exist.
    Cross-check: report statistics must match screenplay flag counts (FR-10).
    """
    raise NotImplementedError("Report generation not yet implemented")


@router.get("")
async def get_report(project_id: str) -> dict:
    """API-26: Get the report artifact envelope."""
    raise NotImplementedError("Report retrieval not yet implemented")
