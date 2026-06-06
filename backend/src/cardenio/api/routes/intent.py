"""Intent and direction API (api.md section 7, API-11~13)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from cardenio.api.deps import get_artifact_store
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.models.intent import IntentConstraints
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/intent")


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
async def set_direction(project_id: str, body: dict) -> dict:
    """API-12: Choose adaptation direction (faithful/cinematic/short_drama)."""
    raise NotImplementedError("Direction setting not yet implemented")


@router.post(":validate")
async def validate_intent(project_id: str) -> dict:
    """API-13: Check for intent-direction conflicts (deterministic)."""
    raise NotImplementedError("Intent validation not yet implemented")
