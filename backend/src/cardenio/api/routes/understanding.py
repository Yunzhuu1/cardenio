"""Understanding (work analysis) API (api.md §5, API-7/8)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/understanding")


@router.post(":generate", status_code=202)
async def generate_understanding(project_id: str) -> dict:
    """API-7: Generate understanding artifact (async Job)."""
    # Gate check: source must have >= 3 chapters
    raise NotImplementedError("Understanding generation not yet implemented")


@router.get("")
async def get_understanding(project_id: str) -> dict:
    """API-8: Get understanding artifact envelope."""
    raise NotImplementedError("Understanding retrieval not yet implemented")


@router.put("")
async def update_understanding(project_id: str, body: dict) -> dict:
    """API-8: Edit understanding artifact (author can modify all fields)."""
    raise NotImplementedError("Understanding update not yet implemented")


@router.post(":confirm")
async def confirm_understanding(project_id: str) -> dict:
    """API-8: Confirm understanding (P1 gate — blocks downstream until confirmed)."""
    raise NotImplementedError("Understanding confirmation not yet implemented")
