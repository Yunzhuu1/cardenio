"""Intent and direction API (api.md §7, API-11~13)."""

from __future__ import annotations

from fastapi import APIRouter

from cardenio.domain.models.intent import IntentConstraints

router = APIRouter(prefix="/projects/{project_id}/intent")


@router.put("")
async def set_intent(project_id: str, intent: IntentConstraints) -> dict:
    """API-11: Set author intent as downstream hard constraints."""
    raise NotImplementedError("Intent setting not yet implemented")


@router.put("/direction")
async def set_direction(project_id: str, body: dict) -> dict:
    """API-12: Choose adaptation direction (faithful/cinematic/short_drama)."""
    raise NotImplementedError("Direction setting not yet implemented")


@router.post(":validate")
async def validate_intent(project_id: str) -> dict:
    """API-13: Check for intent-direction conflicts (deterministic)."""
    raise NotImplementedError("Intent validation not yet implemented")
