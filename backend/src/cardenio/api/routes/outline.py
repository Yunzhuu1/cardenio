"""Outline (scene breakdown) API (api.md §8, API-14~16)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/outline")


@router.post(":generate", status_code=202)
async def generate_outline(project_id: str) -> dict:
    """API-14: Generate scene outline (async Job).

    Gate: understanding and characters must be confirmed.
    """
    raise NotImplementedError("Outline generation not yet implemented")


@router.get("")
async def get_outline(project_id: str) -> dict:
    """API-15: Get outline with scene array."""
    raise NotImplementedError("Outline retrieval not yet implemented")


@router.post("/scenes", status_code=201)
async def add_scene(project_id: str, body: dict) -> dict:
    """API-15: Add a new scene."""
    raise NotImplementedError("Scene creation not yet implemented")


@router.put("/scenes/{scene_id}")
async def update_scene(project_id: str, scene_id: str, body: dict) -> dict:
    """API-15: Edit a scene."""
    raise NotImplementedError("Scene update not yet implemented")


@router.delete("/scenes/{scene_id}", status_code=204)
async def delete_scene(project_id: str, scene_id: str) -> None:
    """API-15: Delete a scene."""
    raise NotImplementedError("Scene deletion not yet implemented")


@router.post("/scenes:reorder")
async def reorder_scenes(project_id: str, body: dict) -> dict:
    """API-15: Reorder scenes."""
    raise NotImplementedError("Scene reordering not yet implemented")


@router.post(":confirm")
async def confirm_outline(project_id: str) -> dict:
    """API-15: Confirm outline (gate — blocks screenplay generation)."""
    raise NotImplementedError("Outline confirmation not yet implemented")


@router.get("/merge-suggestions")
async def get_merge_suggestions(project_id: str) -> dict:
    """API-16: Get merge suggestions (suggestions, not auto-applied)."""
    raise NotImplementedError("Merge suggestions not yet implemented")


@router.post("/merge-suggestions/{suggestion_id}:apply")
async def apply_merge_suggestion(project_id: str, suggestion_id: str) -> dict:
    """API-16: Author accepts a merge suggestion."""
    raise NotImplementedError("Merge application not yet implemented")


@router.post("/merge-suggestions/{suggestion_id}:dismiss")
async def dismiss_merge_suggestion(project_id: str, suggestion_id: str) -> dict:
    """API-16: Author dismisses a merge suggestion."""
    raise NotImplementedError("Merge dismissal not yet implemented")
