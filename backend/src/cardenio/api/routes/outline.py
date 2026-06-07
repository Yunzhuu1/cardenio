"""Outline (scene breakdown) API (api.md section 8, API-14~16)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState
from cardenio.domain.models.outline import (
    MergeSuggestion,
    MergeSuggestionStatus,
    OutlineData,
    OutlineScene,
)
from cardenio.domain.services.outline_service import (
    OutlineService,
    validate_outline_source_refs,
)
from cardenio.gateway.protocol import LlmGateway
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/outline")


class ReorderScenesRequest(BaseModel):
    """Request body for reordering outline scenes."""

    model_config = ConfigDict(extra="forbid")

    order: list[str]


@router.post(":generate", status_code=202)
async def generate_outline(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-14: Generate scene outline.

    Gate: understanding and characters must be confirmed.
    """
    service = OutlineService(gateway=gateway, store=store)
    return await service.generate_outline(project_id)


@router.get("")
async def get_outline(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-15: Get outline with scene array."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "outline")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Outline not found")
    return artifact.model_dump(mode="json")


@router.post("/scenes", status_code=201)
async def add_scene(
    project_id: str,
    body: OutlineScene,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-15: Add a new scene."""
    previous, data = await _get_outline_data(store, project_id)
    if any(scene.id == body.id for scene in data.scenes):
        raise HTTPException(status_code=409, detail="Scene already exists")

    data.scenes.append(body)
    await validate_outline_source_refs(store, project_id, data)
    saved = await _save_outline(store, project_id, data, previous, ArtifactState.DRAFT)
    return saved.model_dump(mode="json")


@router.put("/scenes/{scene_id}")
async def update_scene(
    project_id: str,
    scene_id: str,
    body: OutlineScene,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-15: Edit a scene."""
    previous, data = await _get_outline_data(store, project_id)
    for index, scene in enumerate(data.scenes):
        if scene.id == scene_id:
            data.scenes[index] = body
            await validate_outline_source_refs(store, project_id, data)
            saved = await _save_outline(
                store, project_id, data, previous, ArtifactState.DRAFT
            )
            return saved.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Scene not found")


@router.delete("/scenes/{scene_id}", status_code=204)
async def delete_scene(
    project_id: str,
    scene_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> None:
    """API-15: Delete a scene."""
    previous, data = await _get_outline_data(store, project_id)
    kept = [scene for scene in data.scenes if scene.id != scene_id]
    if len(kept) == len(data.scenes):
        raise HTTPException(status_code=404, detail="Scene not found")

    data.scenes = kept
    await validate_outline_source_refs(store, project_id, data)
    await _save_outline(store, project_id, data, previous, ArtifactState.DRAFT)


@router.post("/scenes:reorder")
async def reorder_scenes(
    project_id: str,
    body: ReorderScenesRequest,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-15: Reorder scenes."""
    previous, data = await _get_outline_data(store, project_id)
    by_id = {scene.id: scene for scene in data.scenes}
    if set(body.order) != set(by_id) or len(body.order) != len(by_id):
        raise HTTPException(status_code=422, detail="Order must include every scene once")

    data.scenes = [by_id[scene_id] for scene_id in body.order]
    saved = await _save_outline(store, project_id, data, previous, ArtifactState.DRAFT)
    return saved.model_dump(mode="json")


@router.post(":confirm")
async def confirm_outline(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-15: Confirm outline (gate blocks screenplay generation)."""
    previous, data = await _get_outline_data(store, project_id)
    await validate_outline_source_refs(store, project_id, data)
    saved = await _save_outline(
        store, project_id, data, previous, ArtifactState.CONFIRMED
    )
    return saved.model_dump(mode="json")


@router.get("/merge-suggestions")
async def get_merge_suggestions(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-16: Get merge suggestions (suggestions, not auto-applied)."""
    previous, data = await _get_outline_data(store, project_id)
    data.merge_suggestions = _merge_suggestions_for(data)
    await _save_outline(store, project_id, data, previous, previous.state)
    return {
        "suggestions": [
            suggestion.model_dump(mode="json")
            for suggestion in data.merge_suggestions
        ]
    }


@router.post("/merge-suggestions/{suggestion_id}:apply")
async def apply_merge_suggestion(
    project_id: str,
    suggestion_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-16: Author accepts a merge suggestion."""
    previous, data = await _get_outline_data(store, project_id)
    suggestion = _find_merge_suggestion(data, suggestion_id)
    suggestion.status = MergeSuggestionStatus.APPLIED
    saved = await _save_outline(store, project_id, data, previous, previous.state)
    return saved.model_dump(mode="json")


@router.post("/merge-suggestions/{suggestion_id}:dismiss")
async def dismiss_merge_suggestion(
    project_id: str,
    suggestion_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-16: Author dismisses a merge suggestion."""
    previous, data = await _get_outline_data(store, project_id)
    suggestion = _find_merge_suggestion(data, suggestion_id)
    suggestion.status = MergeSuggestionStatus.DISMISSED
    saved = await _save_outline(store, project_id, data, previous, previous.state)
    return saved.model_dump(mode="json")


async def _get_outline_data(
    store: SqliteArtifactStore,
    project_id: str,
) -> tuple[ArtifactEnvelope[Any], OutlineData]:
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "outline")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Outline not found")
    return artifact, OutlineData.model_validate(artifact.data)


async def _save_outline(
    store: SqliteArtifactStore,
    project_id: str,
    data: OutlineData,
    previous: ArtifactEnvelope[Any],
    state: ArtifactState,
) -> ArtifactEnvelope[Any]:
    envelope = ArtifactEnvelope[OutlineData](
        type="outline",
        state=state,
        parent_version=previous.version,
        data=data,
    )
    return await store.save_artifact(project_id, envelope)


def _merge_suggestions_for(data: OutlineData) -> list[MergeSuggestion]:
    existing = {suggestion.id: suggestion for suggestion in data.merge_suggestions}
    suggestions: list[MergeSuggestion] = []
    for index, (left, right) in enumerate(
        zip(data.scenes, data.scenes[1:], strict=False),
        start=1,
    ):
        if not _is_merge_candidate(left, right):
            continue
        suggestion_id = f"mg_{left.id}_{right.id}"
        current = existing.get(suggestion_id)
        suggestions.append(
            MergeSuggestion(
                id=suggestion_id,
                scene_ids=[left.id, right.id],
                reason=_merge_reason(left, right),
                status=current.status if current else MergeSuggestionStatus.PENDING,
            )
        )
    return suggestions


def _is_merge_candidate(left: OutlineScene, right: OutlineScene) -> bool:
    light_bridge = _is_light_scene(left) or _is_light_scene(right)
    shared_characters = bool(set(left.characters) & set(right.characters))
    return light_bridge and shared_characters


def _is_light_scene(scene: OutlineScene) -> bool:
    content = " ".join(
        filter(
            None,
            [
                scene.synopsis,
                scene.goal,
                scene.conflict,
                scene.ending_state,
            ],
        )
    ).lower()
    bridge_markers = (
        "transition",
        "bridge",
        "wait",
        "watch",
        "warn",
        "clue",
        "过场",
        "转场",
        "铺垫",
    )
    sparse_fields = (
        not scene.foreshadowing
        and not scene.relation_changes
        and len(scene.characters) <= 2
    )
    return sparse_fields or any(marker in content for marker in bridge_markers)


def _merge_reason(left: OutlineScene, right: OutlineScene) -> str:
    return (
        f"{left.id} and {right.id} are adjacent bridge-like scenes with "
        "overlapping source or staging; consider merging them after author review."
    )


def _find_merge_suggestion(
    data: OutlineData,
    suggestion_id: str,
) -> MergeSuggestion:
    for suggestion in data.merge_suggestions:
        if suggestion.id == suggestion_id:
            return suggestion
    raise HTTPException(status_code=404, detail="Merge suggestion not found")
