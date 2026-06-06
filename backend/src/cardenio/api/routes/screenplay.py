"""Screenplay (generation & editing) API (api.md §9-10, API-17~22)."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/projects/{project_id}/screenplay")


@router.post(":generate", status_code=202)
async def generate_screenplay(project_id: str, body: dict | None = None) -> dict:
    """API-17: Generate screenplay draft (async Job, scene-level fan-out).

    Gate: outline must be confirmed.
    """
    raise NotImplementedError("Screenplay generation not yet implemented")


@router.get("")
async def get_screenplay(project_id: str, *, format: str = "json") -> dict:
    """API-18: Get screenplay (JSON or YAML, FR-9.5 dual view)."""
    raise NotImplementedError("Screenplay retrieval not yet implemented")


@router.get("/scenes/{scene_id}")
async def get_scene(project_id: str, scene_id: str) -> dict:
    """API-18: Get a single scene."""
    raise NotImplementedError("Scene retrieval not yet implemented")


@router.put("")
async def update_screenplay(project_id: str, body: dict) -> dict:
    """API-19: Rewrite full screenplay (YAML or JSON)."""
    raise NotImplementedError("Screenplay update not yet implemented")


@router.put("/scenes/{scene_id}")
async def update_scene(project_id: str, scene_id: str, body: dict) -> dict:
    """API-19: Rewrite a single scene."""
    raise NotImplementedError("Scene update not yet implemented")


@router.get("/beats")
async def get_beats(
    project_id: str, *, flag: str | None = None
) -> dict:
    """API-20: Filter beats by flag (from_source/ai_inferred)."""
    raise NotImplementedError("Beat filtering not yet implemented")


@router.get("/todos")
async def get_todos(project_id: str) -> dict:
    """API-20: Get all todo markers (FR-9.6)."""
    raise NotImplementedError("Todo retrieval not yet implemented")


@router.post("/scenes/{scene_id}:rewrite", status_code=202)
async def rewrite_scene(project_id: str, scene_id: str, body: dict) -> dict:
    """API-21: Local rewrite of a single scene (FR-9.2 core interaction)."""
    raise NotImplementedError("Scene rewrite not yet implemented")


@router.get("/scenes/{scene_id}/versions")
async def get_scene_versions(project_id: str, scene_id: str) -> dict:
    """API-22: List scene version history."""
    raise NotImplementedError("Version history not yet implemented")


@router.post("/scenes/{scene_id}/versions", status_code=201)
async def create_scene_version(project_id: str, scene_id: str, body: dict) -> dict:
    """API-22: Create a branch version for a scene."""
    raise NotImplementedError("Version branching not yet implemented")


@router.post("/scenes/{scene_id}:checkout")
async def checkout_scene_version(project_id: str, scene_id: str, body: dict) -> dict:
    """API-22: Switch to / rollback to a scene version."""
    raise NotImplementedError("Version checkout not yet implemented")


@router.get("/scenes/{scene_id}/versions:diff")
async def diff_scene_versions(project_id: str, scene_id: str, *, a: str, b: str) -> dict:
    """API-22: Compare two scene versions."""
    raise NotImplementedError("Version diff not yet implemented")
