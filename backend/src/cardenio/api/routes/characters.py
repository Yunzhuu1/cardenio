"""Characters (profile) API (api.md section 6, API-9/10)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.models.characters import Character, CharactersData
from cardenio.domain.services.analysis_service import AnalysisService
from cardenio.gateway.protocol import LlmGateway
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/characters")


@router.post(":generate", status_code=202)
async def generate_characters(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-9: Generate character profiles after understanding is confirmed."""
    service = AnalysisService(gateway=gateway, store=store)
    return await service.generate_profiles(project_id)


@router.get("")
async def get_characters(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-10: Get latest characters artifact envelope."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "characters")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Characters not found")
    return artifact.model_dump(mode="json")


@router.post("", status_code=201)
async def add_character(
    project_id: str,
    body: Character,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-10: Manually add a character profile."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "characters")
    characters = _characters_from_artifact(previous)
    if any(character.id == body.id for character in characters):
        raise HTTPException(status_code=409, detail="Character already exists")
    characters.append(body)
    saved = await _save_characters(store, project_id, characters, previous)
    return saved.model_dump(mode="json")


@router.put("/{character_id}")
async def update_character(
    project_id: str,
    character_id: str,
    body: Character,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-10: Edit a character profile; all fields are editable."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "characters")
    characters = _characters_from_artifact(previous)
    for index, character in enumerate(characters):
        if character.id == character_id:
            characters[index] = body
            saved = await _save_characters(store, project_id, characters, previous)
            return saved.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Character not found")


@router.delete("/{character_id}", status_code=204)
async def delete_character(
    project_id: str,
    character_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> None:
    """API-10: Delete a character profile."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "characters")
    characters = _characters_from_artifact(previous)
    kept = [character for character in characters if character.id != character_id]
    if len(kept) == len(characters):
        raise HTTPException(status_code=404, detail="Character not found")
    await _save_characters(store, project_id, kept, previous)


@router.post(":confirm")
async def confirm_characters(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-10: Confirm characters; voice/hard_rules become hard constraints."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "characters")
    if previous is None:
        raise HTTPException(status_code=404, detail="Characters not found")

    data = CharactersData.model_validate(previous.data)
    envelope = ArtifactEnvelope[CharactersData](
        type="characters",
        state=ArtifactState.CONFIRMED,
        parent_version=previous.version,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    if project["state"] == ProjectState.UNDERSTOOD:
        await store.update_project_state(project_id, ProjectState.PROFILED)
    return saved.model_dump(mode="json")


async def _save_characters(
    store: SqliteArtifactStore,
    project_id: str,
    characters: list[Character],
    previous: ArtifactEnvelope[Any] | None,
) -> ArtifactEnvelope[Any]:
    envelope = ArtifactEnvelope[CharactersData](
        type="characters",
        state=ArtifactState.DRAFT,
        parent_version=previous.version if previous else None,
        data=CharactersData(characters=characters),
    )
    return await store.save_artifact(project_id, envelope)


def _characters_from_artifact(
    artifact: ArtifactEnvelope[Any] | None,
) -> list[Character]:
    if artifact is None:
        return []
    data = CharactersData.model_validate(artifact.data)
    return list(data.characters)
