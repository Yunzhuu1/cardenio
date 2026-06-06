"""Settings & privacy API (api.md §13, API-29)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/settings")


@router.get("")
async def get_settings(project_id: str) -> dict:
    """API-29: Get project settings (privacy, shot hints, language)."""
    raise NotImplementedError("Settings retrieval not yet implemented")


@router.put("")
async def update_settings(project_id: str, body: dict) -> dict:
    """API-29: Update project settings."""
    raise NotImplementedError("Settings update not yet implemented")
