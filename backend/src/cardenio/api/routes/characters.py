"""Characters (profile) API (api.md §6, API-9/10)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/characters")


@router.post(":generate", status_code=202)
async def generate_characters(project_id: str) -> dict:
    """API-9: Generate character profiles (async Job).

    Gate: understanding must be confirmed (P1).
    """
    raise NotImplementedError("Character generation not yet implemented")


@router.get("")
async def get_characters(project_id: str) -> dict:
    """API-10: Get all characters and relationship graph."""
    raise NotImplementedError("Character retrieval not yet implemented")


@router.post("", status_code=201)
async def add_character(project_id: str, body: dict) -> dict:
    """API-10: Manually add a character."""
    raise NotImplementedError("Character creation not yet implemented")


@router.put("/{character_id}")
async def update_character(project_id: str, character_id: str, body: dict) -> dict:
    """API-10: Edit a character (all fields editable)."""
    raise NotImplementedError("Character update not yet implemented")


@router.delete("/{character_id}", status_code=204)
async def delete_character(project_id: str, character_id: str) -> None:
    """API-10: Delete a character."""
    raise NotImplementedError("Character deletion not yet implemented")


@router.post(":confirm")
async def confirm_characters(project_id: str) -> dict:
    """API-10: Confirm characters (P1 gate — voice/hard_rules become hard constraints)."""
    raise NotImplementedError("Character confirmation not yet implemented")
