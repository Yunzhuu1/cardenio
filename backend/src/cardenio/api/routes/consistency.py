"""Consistency (rename + conflict check) API (api.md §10, API-23)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/consistency")


@router.post(":rename")
async def rename_character(project_id: str, body: dict) -> dict:
    """API-23: Global character rename (deterministic, FR-9.4).

    Character id is stable; only display name changes.
    """
    raise NotImplementedError("Character rename not yet implemented")


@router.post(":check")
async def check_consistency(project_id: str) -> dict:
    """API-23: Detect character consistency conflicts (FR-9.4).

    Returns a list of conflict **suggestions**, not auto-fixes.
    """
    raise NotImplementedError("Consistency check not yet implemented")
