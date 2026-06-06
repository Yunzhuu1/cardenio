"""Intent and direction API (api.md section 7, API-11~13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from cardenio.api.deps import get_artifact_store
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.models.intent import AdaptationDirection, IntentConstraints
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/intent")
_MVP_DIRECTIONS = {
    AdaptationDirection.FAITHFUL,
    AdaptationDirection.CINEMATIC,
    AdaptationDirection.SHORT_DRAMA,
}


class DirectionRequest(BaseModel):
    """Request body for choosing the MVP adaptation direction."""

    model_config = ConfigDict(extra="forbid")

    direction: AdaptationDirection


@router.put("")
async def set_intent(
    project_id: str,
    intent: IntentConstraints,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-11: Set author intent as downstream hard constraints."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "intent")
    envelope = ArtifactEnvelope[IntentConstraints](
        type="intent",
        state=ArtifactState.CONFIRMED,
        parent_version=previous.version if previous else None,
        data=intent,
    )
    saved = await store.save_artifact(project_id, envelope)
    characters = await store.get_artifact(project_id, "characters")
    if project["state"] == ProjectState.PROFILED or (
        characters is not None and characters.state == ArtifactState.CONFIRMED
    ):
        await store.update_project_state(project_id, ProjectState.INTENT_SET)
    return saved.model_dump(mode="json")


@router.get("")
async def get_intent(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-11: Get latest author intent constraint artifact."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "intent")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Intent not found")
    return artifact.model_dump(mode="json")


@router.put("/direction")
async def set_direction(
    project_id: str,
    body: DirectionRequest,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-12: Choose adaptation direction (faithful/cinematic/short_drama)."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if body.direction not in _MVP_DIRECTIONS:
        raise HTTPException(
            status_code=422,
            detail="direction must be one of faithful, cinematic, short_drama",
        )

    await store.update_project_adaptation_direction(
        project_id, body.direction.value
    )
    updated_project = await store.get_project(project_id)
    return {
        "direction": body.direction.value,
        "project": updated_project,
    }


@router.post(":validate")
async def validate_intent(project_id: str) -> dict:
    """API-13: Check for intent-direction conflicts (deterministic)."""
    raise NotImplementedError("Intent validation not yet implemented")
