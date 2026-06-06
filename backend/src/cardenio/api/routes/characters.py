"""Characters (profile) API (api.md section 6, API-9/10)."""

from __future__ import annotations

import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.models.characters import Character, CharactersData
from cardenio.gateway.protocol import GenerateRequest, LlmGateway, SystemConstraints
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/characters")
_STOP_NAMES = {
    "A",
    "An",
    "And",
    "But",
    "Chapter",
    "He",
    "Her",
    "His",
    "I",
    "It",
    "She",
    "The",
    "They",
    "This",
    "We",
}


@router.post(":generate", status_code=202)
async def generate_characters(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-9: Generate character profiles after understanding is confirmed."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    understanding = await store.get_artifact(project_id, "understanding")
    if understanding is None or understanding.state != ArtifactState.CONFIRMED:
        return _understanding_gate_error(understanding.state if understanding else None)

    chapters = await store.list_chapters(project_id)
    result = await gateway.generate(
        GenerateRequest(
            task="profile",
            system_constraints=SystemConstraints(
                style_fingerprint=project["style_fingerprint"]
            ),
            context=[
                {"type": "understanding", "data": understanding.data},
                *[_chapter_context(chapter) for chapter in chapters],
            ],
            output_schema=CharactersData.model_json_schema(),
        )
    )
    data = CharactersData.model_validate(
        _with_profile_defaults(result.data, chapters, understanding.data)
    )
    previous = await store.get_artifact(project_id, "characters")
    envelope = ArtifactEnvelope[CharactersData](
        type="characters",
        state=ArtifactState.DRAFT,
        parent_version=previous.version if previous else None,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    return saved.model_dump(mode="json")


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


def _understanding_gate_error(current_state: ArtifactState | None) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "state_gate_blocked",
                "message": "Understanding must be confirmed before generating characters",
                "retryable": False,
                "details": {
                    "artifact": "understanding",
                    "required_state": ArtifactState.CONFIRMED.value,
                    "current_state": current_state.value if current_state else "empty",
                },
            }
        },
    )


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


def _chapter_context(chapter: dict[str, Any]) -> dict[str, Any]:
    return {
        "chapter_id": chapter["id"],
        "order": chapter["order"],
        "title": chapter["title"],
        "paragraphs": chapter["paragraphs"],
    }


def _with_profile_defaults(
    generated: dict[str, Any],
    chapters: list[dict[str, Any]],
    understanding: dict[str, Any],
) -> dict[str, Any]:
    if generated.get("characters"):
        return generated
    return {"characters": _extract_character_profiles(chapters, understanding)}


def _extract_character_profiles(
    chapters: list[dict[str, Any]],
    understanding: dict[str, Any],
) -> list[dict[str, Any]]:
    names = _extract_character_names(chapters)
    if not names:
        names = ["Protagonist"]

    characters: list[dict[str, Any]] = []
    for index, name in enumerate(names):
        characters.append(
            {
                "id": _character_id(name),
                "name": name,
                "role": "protagonist" if index == 0 else "supporting",
                "voice": _voice_for(name, understanding),
                "desire": _understanding_field(
                    understanding,
                    "protagonist_goal",
                    "Pursue the central story objective.",
                ),
                "fear": _understanding_field(
                    understanding,
                    "protagonist_fear",
                    "Lose the relationship or secret that anchors the story.",
                ),
                "arc": _arc_for(index),
                "relations": [],
                "hard_rules": [
                    f"{name} must keep a consistent motivation across generated scenes."
                ],
            }
        )
    return characters


def _extract_character_names(chapters: list[dict[str, Any]]) -> list[str]:
    counts: dict[str, int] = {}
    for chapter in chapters:
        for paragraph in chapter["paragraphs"]:
            text = paragraph["text"]
            for name in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", text):
                if name in _STOP_NAMES or name.split()[0] in _STOP_NAMES:
                    continue
                counts[name] = counts.get(name, 0) + 1
    return [
        name
        for name, _count in sorted(
            counts.items(), key=lambda item: (-item[1], item[0])
        )[:8]
    ]


def _character_id(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return normalized or "character"


def _voice_for(name: str, understanding: dict[str, Any]) -> str:
    style = understanding.get("style_fingerprint") or "source-grounded"
    return f"{name} speaks with a {style} voice."


def _understanding_field(
    understanding: dict[str, Any],
    field: str,
    fallback: str,
) -> str:
    value = understanding.get(field)
    if isinstance(value, str) and value.strip():
        return value
    return fallback


def _arc_for(index: int) -> str:
    if index == 0:
        return "Moves from uncertainty toward action."
    return "Pressure-tests the protagonist's choices."
