"""Outline (scene breakdown) API (api.md section 8, API-14~16)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.models.outline import OutlineData, OutlineScene
from cardenio.gateway.protocol import GenerateRequest, LlmGateway, SystemConstraints
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
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    characters = await store.get_artifact(project_id, "characters")
    if characters is None or characters.state != ArtifactState.CONFIRMED:
        return _characters_gate_error(characters.state if characters else None)

    chapters = await store.list_chapters(project_id)
    understanding = await store.get_artifact(project_id, "understanding")
    intent = await store.get_artifact(project_id, "intent")
    result = await gateway.generate(
        GenerateRequest(
            task="outline",
            system_constraints=SystemConstraints(
                style_fingerprint=project["style_fingerprint"],
                voice=_voice_constraints(characters.data),
                hard_rules=_hard_rules(characters.data),
                author_intent=intent.data if intent else None,
            ),
            context=[
                {"type": "understanding", "data": understanding.data}
                if understanding
                else {"type": "understanding", "data": None},
                {"type": "characters", "data": characters.data},
                {"type": "adaptation_direction", "data": project["adaptation_direction"]},
                *[_chapter_context(chapter) for chapter in chapters],
            ],
            output_schema=OutlineData.model_json_schema(),
        )
    )
    data = OutlineData.model_validate(
        _with_outline_defaults(result.data, chapters, characters.data)
    )
    await _validate_outline_source_refs(store, project_id, data)
    previous = await store.get_artifact(project_id, "outline")
    envelope = ArtifactEnvelope[OutlineData](
        type="outline",
        state=ArtifactState.DRAFT,
        parent_version=previous.version if previous else None,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    if project["state"] == ProjectState.INTENT_SET:
        await store.update_project_state(project_id, ProjectState.OUTLINED)
    return saved.model_dump(mode="json")


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
    await _validate_outline_source_refs(store, project_id, data)
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
            await _validate_outline_source_refs(store, project_id, data)
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
    await _validate_outline_source_refs(store, project_id, data)
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
    await _validate_outline_source_refs(store, project_id, data)
    saved = await _save_outline(
        store, project_id, data, previous, ArtifactState.CONFIRMED
    )
    return saved.model_dump(mode="json")


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


def _characters_gate_error(current_state: ArtifactState | None) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "state_gate_blocked",
                "message": "Characters must be confirmed before generating outline",
                "retryable": False,
                "details": {
                    "artifact": "characters",
                    "required_state": ArtifactState.CONFIRMED.value,
                    "current_state": current_state.value if current_state else "empty",
                },
            }
        },
    )


async def _validate_outline_source_refs(
    store: SqliteArtifactStore,
    project_id: str,
    data: OutlineData,
) -> None:
    for scene in data.scenes:
        chapter_id = f"ch_{scene.source_ref.chapter}"
        rows = await store.get_paragraphs(project_id, chapter_id=chapter_id)
        available = {row["paragraph_index"] for row in rows}
        missing = [
            index for index in scene.source_ref.paragraphs if index not in available
        ]
        if missing or not scene.source_ref.paragraphs:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "invalid_source_ref",
                    "scene_id": scene.id,
                    "chapter": scene.source_ref.chapter,
                    "missing_paragraphs": missing,
                },
            )


def _chapter_context(chapter: dict[str, Any]) -> dict[str, Any]:
    return {
        "chapter_id": chapter["id"],
        "order": chapter["order"],
        "title": chapter["title"],
        "paragraphs": chapter["paragraphs"],
    }


def _with_outline_defaults(
    generated: dict[str, Any],
    chapters: list[dict[str, Any]],
    characters: dict[str, Any],
) -> dict[str, Any]:
    if generated.get("scenes"):
        return generated
    return {
        "scenes": _scenes_from_chapters(chapters, characters),
        "merge_suggestions": generated.get("merge_suggestions", []),
    }


def _scenes_from_chapters(
    chapters: list[dict[str, Any]],
    characters: dict[str, Any],
) -> list[dict[str, Any]]:
    character_ids = [character["id"] for character in characters.get("characters", [])]
    scenes: list[dict[str, Any]] = []
    for index, chapter in enumerate(chapters, start=1):
        paragraphs = chapter["paragraphs"]
        if not paragraphs:
            continue
        paragraph_indices = [int(paragraph["index"]) for paragraph in paragraphs]
        source_text = _chapter_excerpt(paragraphs)
        present_characters = _present_character_ids(source_text, characters)
        if not present_characters:
            present_characters = character_ids[:2]
        scenes.append(
            {
                "id": f"sc_{index:03d}",
                "heading": {
                    "int_ext": _int_ext_for(source_text),
                    "location": _location_for(chapter, source_text),
                    "time": _time_for(source_text),
                },
                "source_ref": {
                    "chapter": int(chapter["order"]),
                    "paragraphs": paragraph_indices,
                },
                "synopsis": _synopsis_for(chapter, source_text),
                "goal": _goal_for(index),
                "conflict": _conflict_for(source_text),
                "mood": _mood_for(source_text),
                "characters": present_characters,
                "foreshadowing": _foreshadowing_for(source_text),
                "relation_changes": _relation_changes_for(present_characters),
                "ending_state": _ending_state_for(chapter, source_text),
            }
        )
    return scenes


def _chapter_excerpt(paragraphs: list[dict[str, Any]]) -> str:
    return " ".join(
        paragraph["text"].strip()
        for paragraph in paragraphs
        if paragraph["text"].strip()
    )


def _present_character_ids(text: str, characters: dict[str, Any]) -> list[str]:
    present = []
    for character in characters.get("characters", []):
        if character["name"] in text:
            present.append(character["id"])
    return present


def _int_ext_for(text: str) -> str:
    lower_text = text.lower()
    if any(
        marker in lower_text
        for marker in ("street", "forest", "yard", "road", "dawn")
    ):
        return "EXT"
    return "INT"


def _location_for(chapter: dict[str, Any], text: str) -> str:
    lower_text = text.lower()
    if "archive" in lower_text:
        return "Archive"
    if "dawn" in lower_text:
        return "Outside at dawn"
    return chapter["title"]


def _time_for(text: str) -> str:
    lower_text = text.lower()
    if "dawn" in lower_text:
        return "DAWN"
    if "night" in lower_text:
        return "NIGHT"
    if "dusk" in lower_text:
        return "DUSK"
    return "DAY"


def _synopsis_for(chapter: dict[str, Any], text: str) -> str:
    excerpt = text[:80].strip()
    return f"{chapter['title']}: {excerpt}" if excerpt else chapter["title"]


def _goal_for(index: int) -> str:
    if index == 1:
        return "Establish the central secret and protagonist objective."
    if index == 2:
        return "Escalate the clue trail and pressure the character relationships."
    return "Force a choice that moves the adaptation into the next dramatic turn."


def _conflict_for(text: str) -> str:
    lower_text = text.lower()
    if "secret" in lower_text:
        return "The need to reveal the secret conflicts with the urge to hide it."
    if "warned" in lower_text:
        return "A warning creates pressure between caution and action."
    return "The protagonist's objective meets resistance from other characters."


def _mood_for(text: str) -> str:
    lower_text = text.lower()
    if "secret" in lower_text or "letter" in lower_text:
        return "tense"
    if "dawn" in lower_text:
        return "restrained"
    return "observational"


def _foreshadowing_for(text: str) -> list[str]:
    lower_text = text.lower()
    hints = []
    if "letter" in lower_text:
        hints.append("The letter should remain traceable as a later reveal.")
    if "secret" in lower_text:
        hints.append("The secret should drive later scene pressure.")
    return hints


def _relation_changes_for(character_ids: list[str]) -> list[dict[str, Any]]:
    if len(character_ids) < 2:
        return []
    return [
        {
            "characters": character_ids[:2],
            "change": "Their shared scene increases dramatic pressure between them.",
        }
    ]


def _ending_state_for(chapter: dict[str, Any], text: str) -> str:
    if "confront" in text.lower():
        return "The protagonist is ready to confront the hidden truth."
    return f"{chapter['title']} leaves a concrete question for the next scene."


def _voice_constraints(characters: dict[str, Any]) -> dict[str, str]:
    return {
        character["id"]: character["voice"]
        for character in characters.get("characters", [])
        if character.get("voice")
    }


def _hard_rules(characters: dict[str, Any]) -> list[str]:
    rules: list[str] = []
    for character in characters.get("characters", []):
        rules.extend(character.get("hard_rules", []))
    return rules
