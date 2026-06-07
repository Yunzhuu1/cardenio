"""Screenplay (generation & editing) API (api.md section 9-10, API-17~22)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import (
    ArtifactEnvelope,
    ArtifactState,
    Flag,
    ProjectState,
    SourceRef,
)
from cardenio.domain.models.characters import CharactersData
from cardenio.domain.models.intent import IntentConstraints
from cardenio.domain.models.outline import OutlineData, OutlineScene
from cardenio.domain.models.screenplay import (
    Beat,
    BeatType,
    ScreenplayData,
    ScreenplayScene,
    ShotHints,
)
from cardenio.domain.models.understanding import NonVisualizableMark, UnderstandingData
from cardenio.domain.validation.trust import enforce_must_keep_lines
from cardenio.gateway.protocol import GenerateRequest, LlmGateway, SystemConstraints
from cardenio.orchestrator.trust_enforcer import enforce_pipeline_trust
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/screenplay")


class RewriteSceneRequest(BaseModel):
    """Request body for API-21 local scene rewrite."""

    model_config = ConfigDict(extra="forbid")

    instruction: str

    @field_validator("instruction")
    @classmethod
    def instruction_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("instruction must not be blank")
        return stripped


@router.post(":generate", status_code=202)
async def generate_screenplay(
    project_id: str,
    body: dict | None = None,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-17: Generate screenplay draft from confirmed outline."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    outline_artifact = await store.get_artifact(project_id, "outline")
    if outline_artifact is None or outline_artifact.state != ArtifactState.CONFIRMED:
        return _outline_gate_error(outline_artifact.state if outline_artifact else None)

    outline = OutlineData.model_validate(outline_artifact.data)
    understanding_artifact = await store.get_artifact(project_id, "understanding")
    understanding = (
        UnderstandingData.model_validate(understanding_artifact.data)
        if understanding_artifact is not None
        else None
    )
    characters_artifact = await store.get_artifact(project_id, "characters")
    characters = (
        CharactersData.model_validate(characters_artifact.data)
        if characters_artifact is not None
        else None
    )
    intent_artifact = await store.get_artifact(project_id, "intent")
    intent = (
        IntentConstraints.model_validate(intent_artifact.data)
        if intent_artifact is not None
        else None
    )
    shot_hints_enabled = _shot_hints_enabled(body)
    character_voices = _character_voices(characters)
    result = await gateway.generate(
        GenerateRequest(
            task="scene",
            system_constraints=SystemConstraints(
                style_fingerprint=project["style_fingerprint"],
                voice=character_voices,
                author_intent=intent.model_dump(mode="json") if intent else None,
                shot_hints_enabled=shot_hints_enabled,
            ),
            context=[
                {"type": "outline", "data": outline.model_dump(mode="json")},
                {"type": "character_voices", "data": character_voices},
                {
                    "type": "author_intent",
                    "data": intent.model_dump(mode="json") if intent else {},
                },
                {
                    "type": "non_visualizable",
                    "data": [
                        mark.model_dump(mode="json")
                        for mark in (understanding.non_visualizable if understanding else [])
                    ],
                },
                {"type": "adaptation_direction", "data": project["adaptation_direction"]},
                {
                    "type": "request",
                    "data": {**(body or {}), "shot_hints": shot_hints_enabled},
                },
            ],
            output_schema=ScreenplayData.model_json_schema(),
        )
    )
    data = ScreenplayData.model_validate(
        _with_screenplay_defaults(
            result.data,
            outline,
            understanding,
            character_voices,
            shot_hints_enabled,
        )
    )
    data = data.model_copy(update={"shot_hints": ShotHints(enabled=shot_hints_enabled)})
    data = _enforce_screenplay_trust(data, outline, intent, understanding)
    previous = await store.get_artifact(project_id, "screenplay")
    envelope = ArtifactEnvelope[ScreenplayData](
        type="screenplay",
        state=ArtifactState.DRAFT,
        parent_version=previous.version if previous else None,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    if project["state"] == ProjectState.OUTLINED:
        await store.update_project_state(project_id, ProjectState.GENERATED)
    return saved.model_dump(mode="json")


@router.get("")
async def get_screenplay(
    project_id: str,
    *,
    format: str = "json",
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-18: Get screenplay artifact envelope."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if format != "json":
        raise HTTPException(status_code=422, detail="Only json format is implemented")

    artifact = await store.get_artifact(project_id, "screenplay")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Screenplay not found")
    return artifact.model_dump(mode="json")


@router.get("/scenes/{scene_id}")
async def get_scene(
    project_id: str,
    scene_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-18: Get a single screenplay scene."""
    artifact = await store.get_artifact(project_id, "screenplay")
    if artifact is None:
        project = await store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        raise HTTPException(status_code=404, detail="Screenplay not found")

    data = ScreenplayData.model_validate(artifact.data)
    for scene in data.scenes:
        if scene.id == scene_id:
            return scene.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Scene not found")


@router.get("/scenes/{scene_id}/trace")
async def get_scene_trace(
    project_id: str,
    scene_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-24: Resolve a screenplay scene to its source paragraphs."""
    artifact = await store.get_artifact(project_id, "screenplay")
    if artifact is None:
        project = await store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        raise HTTPException(status_code=404, detail="Screenplay not found")

    data = ScreenplayData.model_validate(artifact.data)
    scene = _find_scene(data, scene_id)
    paragraphs = await _resolve_source_ref(store, project_id, scene.source_ref)
    if not paragraphs:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "source_ref_not_found",
                "scene_id": scene.id,
                "source_ref": scene.source_ref.model_dump(mode="json"),
            },
        )

    return {
        "scene_id": scene.id,
        "source_ref": scene.source_ref.model_dump(mode="json"),
        "paragraphs": paragraphs,
        "beats": _traceable_beats(scene),
    }


@router.put("")
async def update_screenplay(
    project_id: str,
    body: ScreenplayData,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-19: Rewrite full screenplay (YAML or JSON)."""
    previous, _ = await _get_screenplay_data(store, project_id)
    _validate_edit_trust_fields(body)
    saved = await _save_screenplay(store, project_id, body, previous)
    await _mark_project_editing(store, project_id)
    return saved.model_dump(mode="json")


@router.put("/scenes/{scene_id}")
async def update_scene(
    project_id: str,
    scene_id: str,
    body: ScreenplayScene,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-19: Rewrite a single scene."""
    if body.id != scene_id:
        raise HTTPException(
            status_code=422,
            detail="Scene id in request body must match path scene_id",
        )

    previous, data = await _get_screenplay_data(store, project_id)
    scenes = []
    found = False
    for scene in data.scenes:
        if scene.id == scene_id:
            scenes.append(body)
            found = True
        else:
            scenes.append(scene)
    if not found:
        raise HTTPException(status_code=404, detail="Scene not found")

    updated = data.model_copy(update={"scenes": scenes})
    _validate_edit_trust_fields(updated)
    saved = await _save_screenplay(store, project_id, updated, previous)
    await _mark_project_editing(store, project_id)
    return saved.model_dump(mode="json")


@router.get("/beats")
async def get_beats(
    project_id: str,
    *,
    flag: str | None = None,
    source_chapter: int | None = Query(default=None, ge=1),
    source_paragraph: int | None = Query(default=None, ge=1),
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-20/API-24: Filter beats by trust markers or source reference."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if (source_chapter is None) != (source_paragraph is None):
        raise HTTPException(
            status_code=422,
            detail="source_chapter and source_paragraph must be provided together",
        )

    requested_flag = _parse_flag(flag)
    artifact = await store.get_artifact(project_id, "screenplay")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Screenplay not found")

    data = ScreenplayData.model_validate(artifact.data)
    items = []
    for scene in data.scenes:
        for beat_index, beat in enumerate(scene.beats):
            if requested_flag is not None and beat.flag != requested_flag:
                continue
            if not _matches_source_ref(beat.source_ref, source_chapter, source_paragraph):
                continue
            items.append(
                {
                    "scene_id": scene.id,
                    "beat_index": beat_index,
                    "beat": beat.model_dump(mode="json"),
                }
            )
    return {"items": items, "count": len(items)}


@router.get("/todos")
async def get_todos(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-20: Get all todo markers (FR-9.6)."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "screenplay")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Screenplay not found")

    data = ScreenplayData.model_validate(artifact.data)
    items = []
    for scene in data.scenes:
        for beat_index, beat in enumerate(scene.beats):
            if beat.type != BeatType.TODO:
                continue
            items.append(
                {
                    "scene_id": scene.id,
                    "beat_index": beat_index,
                    "source_ref": beat.source_ref.model_dump(mode="json")
                    if beat.source_ref
                    else None,
                    "beat": beat.model_dump(mode="json"),
                }
            )
    return {"items": items, "count": len(items)}


@router.post("/scenes/{scene_id}:rewrite", status_code=202)
async def rewrite_scene(
    project_id: str,
    scene_id: str,
    body: RewriteSceneRequest,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-21: Local rewrite of a single scene (FR-9.2 core interaction)."""
    previous, data = await _get_screenplay_data(store, project_id)
    project = await store.get_project(project_id)
    target_index = _find_scene_index(data, scene_id)
    target_scene = data.scenes[target_index]
    characters = await _get_optional_artifact(
        store, project_id, "characters", CharactersData
    )
    intent = await _get_optional_artifact(store, project_id, "intent", IntentConstraints)
    understanding = await _get_optional_artifact(
        store, project_id, "understanding", UnderstandingData
    )
    outline = await _get_optional_artifact(store, project_id, "outline", OutlineData)
    character_voices = _character_voices(characters)
    source_paragraphs = await _resolve_source_ref(
        store, project_id, target_scene.source_ref
    )

    result = await gateway.generate(
        GenerateRequest(
            task="rewrite",
            system_constraints=SystemConstraints(
                style_fingerprint=project["style_fingerprint"] if project else None,
                voice=character_voices,
                author_intent=intent.model_dump(mode="json") if intent else None,
                shot_hints_enabled=data.shot_hints.enabled,
            ),
            context=[
                {
                    "type": "rewrite_request",
                    "data": {
                        "instruction": body.instruction,
                        "scene_id": scene_id,
                    },
                },
                {
                    "type": "target_scene",
                    "data": target_scene.model_dump(mode="json"),
                },
                {
                    "type": "adjacent_scenes",
                    "data": _adjacent_scene_context(data.scenes, target_index),
                },
                {"type": "source_paragraphs", "data": source_paragraphs},
                {"type": "character_voices", "data": character_voices},
                {
                    "type": "author_intent",
                    "data": intent.model_dump(mode="json") if intent else {},
                },
                {
                    "type": "understanding",
                    "data": understanding.model_dump(mode="json")
                    if understanding
                    else {},
                },
            ],
            output_schema=ScreenplayScene.model_json_schema(),
        )
    )

    rewritten_scene = _coerce_rewrite_result(result.data, target_scene, body.instruction)
    rewritten_scene = _enforce_rewrite_scene_trust(
        rewritten_scene,
        target_scene,
        intent,
    )
    if outline is not None:
        rewritten_scene = _annotate_subtext_and_mood(
            [rewritten_scene],
            outline,
            intent,
            understanding,
        )[0]

    scenes = [*data.scenes]
    scenes[target_index] = rewritten_scene
    updated = data.model_copy(update={"scenes": scenes})
    _validate_edit_trust_fields(updated)
    saved = await _save_screenplay(store, project_id, updated, previous)
    await _mark_project_editing(store, project_id)
    return saved.model_dump(mode="json")


@router.get("/scenes/{scene_id}/versions")
async def get_scene_versions(
    project_id: str,
    scene_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-22: List scene version history."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    versions = await store.list_artifact_versions(project_id, "screenplay")
    if not versions:
        raise HTTPException(status_code=404, detail="Screenplay not found")

    items = []
    for artifact in versions:
        data = ScreenplayData.model_validate(artifact.data)
        scene = _find_scene_or_none(data, scene_id)
        if scene is None:
            continue
        items.append(_scene_version_item(artifact, scene))

    if not items:
        raise HTTPException(status_code=404, detail="Scene not found")
    return {"items": items, "count": len(items)}


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


def _outline_gate_error(current_state: ArtifactState | None) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "state_gate_blocked",
                "message": "Outline must be confirmed before generating screenplay",
                "retryable": False,
                "details": {
                    "artifact": "outline",
                    "required_state": ArtifactState.CONFIRMED.value,
                    "current_state": current_state.value if current_state else "empty",
                },
            }
        },
    )


def _with_screenplay_defaults(
    generated: dict[str, Any],
    outline: OutlineData,
    understanding: UnderstandingData | None,
    character_voices: dict[str, str],
    shot_hints_enabled: bool,
) -> dict[str, Any]:
    if generated.get("scenes"):
        return {**generated, "shot_hints": {"enabled": shot_hints_enabled}}
    return {
        "scenes": [
            _scene_from_outline(
                scene,
                _matching_non_visualizable_marks(scene, understanding),
                character_voices,
            )
            for scene in outline.scenes
        ],
        "shot_hints": {"enabled": shot_hints_enabled},
    }


def _shot_hints_enabled(body: dict | None) -> bool:
    if body is None or "shot_hints" not in body:
        return False
    return bool(body["shot_hints"])


def _enforce_screenplay_trust(
    data: ScreenplayData,
    outline: OutlineData,
    intent: IntentConstraints | None,
    understanding: UnderstandingData | None,
) -> ScreenplayData:
    source_paragraph_indices = {
        paragraph
        for scene in outline.scenes
        for paragraph in scene.source_ref.paragraphs
    }
    scenes = enforce_pipeline_trust(
        data.scenes,
        source_paragraph_indices=source_paragraph_indices,
    )
    scenes = _annotate_subtext_and_mood(scenes, outline, intent, understanding)
    scenes = _backfill_dialogue_source_refs(scenes)
    scenes = _ensure_must_keep_lines(scenes, intent.must_keep_lines if intent else [])
    if intent and intent.must_keep_lines:
        enforce_must_keep_lines(
            [beat for scene in scenes for beat in scene.beats],
            intent.must_keep_lines,
        )
    return data.model_copy(update={"scenes": scenes})


def _annotate_subtext_and_mood(
    scenes: list[ScreenplayScene],
    outline: OutlineData,
    intent: IntentConstraints | None,
    understanding: UnderstandingData | None,
) -> list[ScreenplayScene]:
    outline_by_id = {scene.id: scene for scene in outline.scenes}
    annotated: list[ScreenplayScene] = []
    for scene in scenes:
        outline_scene = outline_by_id.get(scene.id)
        fallback_mood = _scene_mood(outline_scene, intent, understanding)
        mood = _style_guarded_mood(
            scene.mood or fallback_mood,
            fallback_mood,
            outline_scene,
            intent,
            understanding,
        )
        beats = [
            beat
            if beat.type == BeatType.TODO or beat.subtext
            else beat.model_copy(
                update={"subtext": _beat_subtext(beat, scene, outline_scene, mood)}
            )
            for beat in scene.beats
        ]
        annotated.append(scene.model_copy(update={"mood": mood, "beats": beats}))
    return annotated


def _scene_mood(
    outline_scene: OutlineScene | None,
    intent: IntentConstraints | None,
    understanding: UnderstandingData | None,
) -> str:
    if outline_scene and outline_scene.mood:
        return outline_scene.mood
    if intent and intent.mood_floor:
        return intent.mood_floor
    if understanding and understanding.mood:
        return understanding.mood
    return "controlled tension"


def _style_guarded_mood(
    candidate: str,
    fallback: str,
    outline_scene: OutlineScene | None,
    intent: IntentConstraints | None,
    understanding: UnderstandingData | None,
) -> str:
    anchor_text = " ".join(
        part
        for part in [
            outline_scene.mood if outline_scene else None,
            intent.mood_floor if intent else None,
            understanding.mood if understanding else None,
            understanding.style_fingerprint if understanding else None,
        ]
        if part
    )
    if not anchor_text:
        return candidate
    if _mood_conflicts_with_style_anchor(candidate, anchor_text):
        return fallback
    return candidate


def _mood_conflicts_with_style_anchor(candidate: str, anchor_text: str) -> bool:
    candidate_lower = candidate.lower()
    anchor_lower = anchor_text.lower()
    serious_anchors = (
        "dark",
        "dread",
        "noir",
        "suspense",
        "suspenseful",
        "tense",
        "restrained",
        "cold",
        "bleak",
        "fear",
        "secret",
    )
    light_moods = (
        "light",
        "humorous",
        "comedy",
        "comic",
        "cheerful",
        "playful",
        "warm",
        "bright",
        "romantic comedy",
    )
    return any(marker in anchor_lower for marker in serious_anchors) and any(
        marker in candidate_lower for marker in light_moods
    )


def _beat_subtext(
    beat: Beat,
    scene: ScreenplayScene,
    outline_scene: OutlineScene | None,
    mood: str,
) -> str:
    if beat.type in {BeatType.DIALOGUE, BeatType.VOICE_OVER, BeatType.OFF_SCREEN}:
        objective = scene.goal or (outline_scene.goal if outline_scene else None)
        return _join_subtext_parts(
            [
                f"Spoken against {mood}.",
                f"Underlying intent: {objective}." if objective else None,
            ]
        )
    if beat.type == BeatType.ACTION:
        conflict = scene.conflict or (outline_scene.conflict if outline_scene else None)
        return _join_subtext_parts(
            [
                f"Action carries {mood}.",
                f"Pressure point: {conflict}." if conflict else None,
            ]
        )
    if beat.type == BeatType.NOTE:
        return f"Adaptation note under {mood}."
    return f"Beat emotional state: {mood}."


def _join_subtext_parts(parts: list[str | None]) -> str:
    return " ".join(part for part in parts if part)


def _backfill_dialogue_source_refs(
    scenes: list[ScreenplayScene],
) -> list[ScreenplayScene]:
    sourced_scenes: list[ScreenplayScene] = []
    dialogue_types = {BeatType.DIALOGUE, BeatType.VOICE_OVER, BeatType.OFF_SCREEN}
    for scene in scenes:
        beats = [
            beat.model_copy(update={"source_ref": scene.source_ref})
            if beat.type in dialogue_types and beat.source_ref is None
            else beat
            for beat in scene.beats
        ]
        sourced_scenes.append(scene.model_copy(update={"beats": beats}))
    return sourced_scenes


def _ensure_must_keep_lines(
    scenes: list[ScreenplayScene],
    must_keep_lines: list[str],
) -> list[ScreenplayScene]:
    missing = [
        line
        for line in must_keep_lines
        if not any(beat.dialogue == line for scene in scenes for beat in scene.beats)
    ]
    if not missing or not scenes:
        return scenes

    target = scenes[0]
    character = target.characters[0] if target.characters else None
    beats = [
        *target.beats,
        *[
            Beat(
                type=BeatType.DIALOGUE,
                character=character,
                dialogue=line,
                source_ref=target.source_ref,
                flag=Flag.FROM_SOURCE,
            )
            for line in missing
        ],
    ]
    return [target.model_copy(update={"beats": beats}), *scenes[1:]]


def _parse_flag(flag: str | None) -> Flag | None:
    if flag is None:
        return None
    try:
        return Flag(flag)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail="flag must be one of: from_source, ai_inferred",
        ) from exc


def _matches_source_ref(
    source_ref: SourceRef | None,
    source_chapter: int | None,
    source_paragraph: int | None,
) -> bool:
    if source_chapter is None and source_paragraph is None:
        return True
    if source_ref is None:
        return False
    return (
        source_ref.chapter == source_chapter
        and source_paragraph in source_ref.paragraphs
    )


def _find_scene(data: ScreenplayData, scene_id: str) -> ScreenplayScene:
    for scene in data.scenes:
        if scene.id == scene_id:
            return scene
    raise HTTPException(status_code=404, detail="Scene not found")


def _find_scene_or_none(
    data: ScreenplayData, scene_id: str
) -> ScreenplayScene | None:
    for scene in data.scenes:
        if scene.id == scene_id:
            return scene
    return None


def _find_scene_index(data: ScreenplayData, scene_id: str) -> int:
    for index, scene in enumerate(data.scenes):
        if scene.id == scene_id:
            return index
    raise HTTPException(status_code=404, detail="Scene not found")


def _adjacent_scene_context(
    scenes: list[ScreenplayScene],
    target_index: int,
) -> dict[str, Any]:
    context: dict[str, Any] = {}
    if target_index > 0:
        context["previous"] = _scene_summary(scenes[target_index - 1])
    if target_index + 1 < len(scenes):
        context["next"] = _scene_summary(scenes[target_index + 1])
    return context


def _scene_summary(scene: ScreenplayScene) -> dict[str, Any]:
    return {
        "id": scene.id,
        "heading": scene.heading.model_dump(mode="json"),
        "source_ref": scene.source_ref.model_dump(mode="json"),
        "synopsis": scene.synopsis,
        "goal": scene.goal,
        "conflict": scene.conflict,
        "mood": scene.mood,
        "characters": scene.characters,
        "ending_state": scene.ending_state,
    }


def _scene_version_item(
    artifact: ArtifactEnvelope[Any],
    scene: ScreenplayScene,
) -> dict[str, Any]:
    return {
        "version": artifact.version,
        "parent_version": artifact.parent_version,
        "state": artifact.state.value,
        "updated_at": artifact.updated_at,
        "needs_recompute": artifact.needs_recompute,
        "scene": scene.model_dump(mode="json"),
    }


def _coerce_rewrite_result(
    generated: dict[str, Any],
    target_scene: ScreenplayScene,
    instruction: str,
) -> ScreenplayScene:
    candidate = _extract_rewrite_scene(generated, target_scene.id)
    if candidate is None:
        candidate = _fallback_rewrite_scene(target_scene, instruction)

    target = target_scene.model_dump(mode="json")
    target.update(candidate)
    target["id"] = target_scene.id
    target["source_ref"] = target_scene.source_ref.model_dump(mode="json")
    if not target.get("beats"):
        target["beats"] = target_scene.model_dump(mode="json")["beats"]
    return ScreenplayScene.model_validate(target)


def _extract_rewrite_scene(
    generated: dict[str, Any],
    scene_id: str,
) -> dict[str, Any] | None:
    if not generated or generated.get("stub") is True:
        return None
    if isinstance(generated.get("scene"), dict):
        return generated["scene"]
    scenes = generated.get("scenes")
    if isinstance(scenes, list) and scenes:
        for scene in scenes:
            if isinstance(scene, dict) and scene.get("id") == scene_id:
                return scene
        first_scene = scenes[0]
        if isinstance(first_scene, dict):
            return first_scene
    if "heading" in generated or "beats" in generated:
        return generated
    return None


def _fallback_rewrite_scene(
    target_scene: ScreenplayScene,
    instruction: str,
) -> dict[str, Any]:
    data = target_scene.model_dump(mode="json")
    beats = [*data["beats"]]
    beats.append(
        Beat(
            type=BeatType.NOTE,
            text=f"Rewrite instruction: {instruction}",
            source_ref=target_scene.source_ref,
            flag=Flag.AI_INFERRED,
        ).model_dump(mode="json")
    )
    data["beats"] = beats
    return data


def _enforce_rewrite_scene_trust(
    rewritten_scene: ScreenplayScene,
    target_scene: ScreenplayScene,
    intent: IntentConstraints | None,
) -> ScreenplayScene:
    beats = [
        _backfill_rewrite_beat_trust(beat, target_scene.source_ref)
        for beat in rewritten_scene.beats
    ]
    scene = rewritten_scene.model_copy(update={"beats": beats})
    enforced = enforce_pipeline_trust(
        [scene],
        source_paragraph_indices=set(target_scene.source_ref.paragraphs),
        intent=intent,
    )[0]
    return _backfill_dialogue_source_refs([enforced])[0]


def _backfill_rewrite_beat_trust(beat: Beat, source_ref: SourceRef) -> Beat:
    if beat.type == BeatType.TODO:
        return beat
    updates: dict[str, Any] = {}
    if beat.source_ref is None:
        updates["source_ref"] = source_ref
    if beat.flag is None:
        updates["flag"] = Flag.AI_INFERRED
    if updates:
        return beat.model_copy(update=updates)
    return beat


def _validate_edit_trust_fields(data: ScreenplayData) -> None:
    missing: list[dict[str, Any]] = []
    for scene in data.scenes:
        for beat_index, beat in enumerate(scene.beats):
            if beat.type == BeatType.TODO:
                continue
            fields = []
            if beat.source_ref is None:
                fields.append("source_ref")
            if beat.flag is None:
                fields.append("flag")
            if fields:
                missing.append(
                    {
                        "scene_id": scene.id,
                        "beat_index": beat_index,
                        "fields": fields,
                    }
                )
    if missing:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "missing_trust_fields",
                "message": "Non-TODO beats must keep source_ref and flag",
                "items": missing,
            },
        )


async def _get_screenplay_data(
    store: SqliteArtifactStore,
    project_id: str,
) -> tuple[ArtifactEnvelope[Any], ScreenplayData]:
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "screenplay")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Screenplay not found")
    return artifact, ScreenplayData.model_validate(artifact.data)


async def _save_screenplay(
    store: SqliteArtifactStore,
    project_id: str,
    data: ScreenplayData,
    previous: ArtifactEnvelope[Any],
) -> ArtifactEnvelope[Any]:
    envelope = ArtifactEnvelope[ScreenplayData](
        type="screenplay",
        state=ArtifactState.DRAFT,
        parent_version=previous.version,
        data=data,
    )
    return await store.save_artifact(project_id, envelope)


async def _mark_project_editing(
    store: SqliteArtifactStore,
    project_id: str,
) -> None:
    project = await store.get_project(project_id)
    if project is not None and project["state"] != ProjectState.EDITING:
        await store.update_project_state(project_id, ProjectState.EDITING)


async def _get_optional_artifact(
    store: SqliteArtifactStore,
    project_id: str,
    artifact_type: str,
    model: type[BaseModel],
) -> Any | None:
    artifact = await store.get_artifact(project_id, artifact_type)
    if artifact is None:
        return None
    return model.model_validate(artifact.data)


async def _resolve_source_ref(
    store: SqliteArtifactStore,
    project_id: str,
    source_ref: SourceRef,
) -> list[dict[str, Any]]:
    chapter_id = f"ch_{source_ref.chapter}"
    rows = await store.get_paragraphs(project_id, chapter_id=chapter_id)
    by_index = {row["paragraph_index"]: row["text"] for row in rows}
    if not by_index:
        return []
    resolved = [
        {"index": index, "text": by_index[index]}
        for index in source_ref.paragraphs
        if index in by_index
    ]
    if len(resolved) != len(source_ref.paragraphs):
        return []
    return resolved


def _traceable_beats(scene: ScreenplayScene) -> list[dict[str, Any]]:
    return [
        {
            "beat_index": beat_index,
            "source_ref": beat.source_ref.model_dump(mode="json")
            if beat.source_ref
            else None,
            "flag": beat.flag.value if beat.flag else None,
            "type": beat.type.value,
        }
        for beat_index, beat in enumerate(scene.beats)
    ]


def _scene_from_outline(
    scene: OutlineScene,
    non_visualizable: list[NonVisualizableMark],
    character_voices: dict[str, str],
) -> dict[str, Any]:
    screenplay_scene = ScreenplayScene(
        id=scene.id,
        heading=scene.heading,
        source_ref=scene.source_ref,
        synopsis=scene.synopsis,
        goal=scene.goal,
        conflict=scene.conflict,
        mood=scene.mood,
        characters=scene.characters,
        foreshadowing=scene.foreshadowing,
        relation_changes=scene.relation_changes,
        ending_state=scene.ending_state,
        beats=_beats_from_outline(scene, non_visualizable, character_voices),
    )
    return screenplay_scene.model_dump(mode="json")


def _beats_from_outline(
    scene: OutlineScene,
    non_visualizable: list[NonVisualizableMark],
    character_voices: dict[str, str],
) -> list[Beat]:
    beats = [
        Beat(
            type=BeatType.ACTION,
            text=_action_text(scene),
            subtext=scene.conflict,
            source_ref=scene.source_ref,
            flag=Flag.FROM_SOURCE,
        )
    ]
    if scene.characters:
        character_id = scene.characters[0]
        voice = character_voices.get(character_id)
        beats.append(
            Beat(
                type=BeatType.DIALOGUE,
                character=character_id,
                parenthetical=_parenthetical_for_voice(voice),
                dialogue=_dialogue_text(scene, voice),
                subtext=_dialogue_subtext(scene, voice),
                source_ref=scene.source_ref,
                flag=Flag.FROM_SOURCE,
            )
        )
    beats.append(
        Beat(
            type=BeatType.ACTION,
            text=_ending_action(scene),
            subtext=scene.ending_state,
            source_ref=scene.source_ref,
            flag=Flag.FROM_SOURCE,
        )
    )
    for mark in non_visualizable:
        beats.append(_externalization_note(scene, mark))
    return beats


def _character_voices(characters: CharactersData | None) -> dict[str, str]:
    if characters is None:
        return {}
    return {
        character.id: character.voice
        for character in characters.characters
        if character.voice.strip()
    }


def _matching_non_visualizable_marks(
    scene: OutlineScene,
    understanding: UnderstandingData | None,
) -> list[NonVisualizableMark]:
    if understanding is None:
        return []
    scene_paragraphs = set(scene.source_ref.paragraphs)
    return [
        mark
        for mark in understanding.non_visualizable
        if mark.source_ref.chapter == scene.source_ref.chapter
        and bool(scene_paragraphs & set(mark.source_ref.paragraphs))
    ]


def _externalization_note(
    scene: OutlineScene,
    mark: NonVisualizableMark,
) -> Beat:
    lead_character = scene.characters[0] if scene.characters else None
    return Beat(
        type=BeatType.NOTE,
        text=(
            f"Non-visualizable source passage requires externalization: {mark.note}"
        ),
        source_ref=mark.source_ref,
        flag=Flag.AI_INFERRED,
        options=[
            {
                "kind": "voice_over",
                "text": "Use V.O. to preserve the inner thought without inventing dialogue.",
            },
            {
                "kind": "action",
                "text": "Translate the mental state into a concrete gesture or choice.",
            },
            {
                "kind": "dialogue",
                "text": (
                    f"Let {lead_character or 'a character'} externalize only what can "
                    "be defended by the source."
                ),
            },
            {
                "kind": "annotation",
                "text": "Keep this as an author/director note if it should not be performed.",
            },
        ],
    )


def _action_text(scene: OutlineScene) -> str:
    return (
        f"{scene.heading.location}. {scene.synopsis} "
        f"The scene moves through {scene.mood or 'controlled'} pressure."
    )


def _dialogue_text(scene: OutlineScene, voice: str | None) -> str:
    pressure = _dialogue_pressure(scene)
    if _prefers_indirect_voice(voice):
        return f"You already know {pressure}."
    if _prefers_clipped_voice(voice):
        return f"Enough. {pressure}."
    return f"We face it now: {pressure}."


def _dialogue_pressure(scene: OutlineScene) -> str:
    if scene.conflict:
        return _compact_sentence(scene.conflict)
    if scene.goal:
        return _compact_sentence(scene.goal)
    return "this cannot wait"


def _compact_sentence(text: str) -> str:
    cleaned = text.strip().rstrip(".")
    if len(cleaned) <= 72:
        return cleaned
    return f"{cleaned[:69].rstrip()}..."


def _parenthetical_for_voice(voice: str | None) -> str | None:
    if voice is None:
        return "(plain)"
    lowered = voice.lower()
    if "quiet" in lowered or "clipped" in lowered or "restrained" in lowered:
        return "(quiet, clipped)"
    if "indirect" in lowered:
        return "(indirect)"
    return "(in character)"


def _dialogue_subtext(scene: OutlineScene, voice: str | None) -> str:
    parts = []
    if scene.goal:
        parts.append(scene.goal)
    if voice:
        parts.append(f"Voice: {voice}")
    return "; ".join(parts) if parts else "Voice-constrained spoken line."


def _prefers_indirect_voice(voice: str | None) -> bool:
    return voice is not None and "indirect" in voice.lower()


def _prefers_clipped_voice(voice: str | None) -> bool:
    if voice is None:
        return False
    lowered = voice.lower()
    return "clipped" in lowered or "quiet" in lowered or "restrained" in lowered


def _ending_action(scene: OutlineScene) -> str:
    if scene.ending_state:
        return scene.ending_state
    return "The scene lands on a clear dramatic turn."
