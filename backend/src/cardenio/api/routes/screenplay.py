"""Screenplay (generation & editing) API (api.md section 9-10, API-17~22)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, Flag, ProjectState
from cardenio.domain.models.outline import OutlineData, OutlineScene
from cardenio.domain.models.screenplay import Beat, BeatType, ScreenplayData, ScreenplayScene
from cardenio.domain.models.understanding import NonVisualizableMark, UnderstandingData
from cardenio.gateway.protocol import GenerateRequest, LlmGateway, SystemConstraints
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/screenplay")


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
    result = await gateway.generate(
        GenerateRequest(
            task="scene",
            system_constraints=SystemConstraints(
                style_fingerprint=project["style_fingerprint"],
                shot_hints_enabled=False,
            ),
            context=[
                {"type": "outline", "data": outline.model_dump(mode="json")},
                {
                    "type": "non_visualizable",
                    "data": [
                        mark.model_dump(mode="json")
                        for mark in (understanding.non_visualizable if understanding else [])
                    ],
                },
                {"type": "adaptation_direction", "data": project["adaptation_direction"]},
                {"type": "request", "data": body or {}},
            ],
            output_schema=ScreenplayData.model_json_schema(),
        )
    )
    data = ScreenplayData.model_validate(
        _with_screenplay_defaults(result.data, outline, understanding)
    )
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
) -> dict[str, Any]:
    if generated.get("scenes"):
        return generated
    return {
        "scenes": [
            _scene_from_outline(
                scene,
                _matching_non_visualizable_marks(scene, understanding),
            )
            for scene in outline.scenes
        ],
        "shot_hints": generated.get("shot_hints", {"enabled": False}),
    }


def _scene_from_outline(
    scene: OutlineScene,
    non_visualizable: list[NonVisualizableMark],
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
        beats=_beats_from_outline(scene, non_visualizable),
    )
    return screenplay_scene.model_dump(mode="json")


def _beats_from_outline(
    scene: OutlineScene,
    non_visualizable: list[NonVisualizableMark],
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
        beats.append(
            Beat(
                type=BeatType.DIALOGUE,
                character=scene.characters[0],
                parenthetical="(keeps control)",
                dialogue=_dialogue_text(scene),
                subtext=scene.goal,
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


def _dialogue_text(scene: OutlineScene) -> str:
    if scene.conflict:
        return f"We cannot ignore this: {scene.conflict}"
    return "We need to decide before this goes further."


def _ending_action(scene: OutlineScene) -> str:
    if scene.ending_state:
        return scene.ending_state
    return "The scene lands on a clear dramatic turn."
