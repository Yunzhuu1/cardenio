"""Generation service — screenplay generation with scene-level fan-out (FR-7, M5)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, Flag, ProjectState
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
from cardenio.domain.runtime import AgentRuntime
from cardenio.domain.tools import SceneGenerateTool, SceneGenerateToolInput, ToolRegistry
from cardenio.domain.validation.trust import enforce_must_keep_lines
from cardenio.gateway.protocol import LlmGateway
from cardenio.orchestrator.gates import generation_gate_response
from cardenio.orchestrator.trust_enforcer import enforce_pipeline_trust
from cardenio.storage.sqlite_store import SqliteArtifactStore

SCENE_GENERATE_TOOL = "scene.generate"


class GenerationService:
    """Orchestrates screenplay generation: fan-out per scene, trust enforcement.

    Scene generation is the unique parallel point (agent-workflow §4.2).
    Each scene is independent; failures don't affect other scenes (NFR-6).
    """

    def __init__(
        self,
        *,
        gateway: LlmGateway,
        store: SqliteArtifactStore,
        runtime: AgentRuntime | None = None,
        tools: ToolRegistry | None = None,
    ) -> None:
        self.gateway = gateway
        self.store = store
        self.runtime = runtime or AgentRuntime()
        self.tools = tools or ToolRegistry(
            [SceneGenerateTool(gateway=self.gateway, runtime=self.runtime)]
        )

    async def generate_screenplay(
        self,
        project_id: str,
        *,
        body: dict | None = None,
        scene_ids: list[str] | None = None,
    ) -> dict | JSONResponse:
        """Generate screenplay draft. Fan-out per scene (FR-7)."""
        project = await self.store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        outline_artifact = await self.store.get_artifact(project_id, "outline")
        gate_error = generation_gate_response(
            "screenplay:generate",
            {"outline": outline_artifact},
        )
        if gate_error is not None:
            return gate_error

        outline = OutlineData.model_validate(outline_artifact.data)
        if scene_ids is not None:
            outline = outline.model_copy(
                update={
                    "scenes": [scene for scene in outline.scenes if scene.id in scene_ids]
                }
            )
        understanding_artifact = await self.store.get_artifact(project_id, "understanding")
        understanding = (
            UnderstandingData.model_validate(understanding_artifact.data)
            if understanding_artifact is not None
            else None
        )
        characters_artifact = await self.store.get_artifact(project_id, "characters")
        characters = (
            CharactersData.model_validate(characters_artifact.data)
            if characters_artifact is not None
            else None
        )
        intent_artifact = await self.store.get_artifact(project_id, "intent")
        intent = (
            IntentConstraints.model_validate(intent_artifact.data)
            if intent_artifact is not None
            else None
        )
        shot_hints_enabled = shot_hints_enabled_from_body(body)
        character_voices = character_voices_for(characters)
        result = await self.tools.get(SCENE_GENERATE_TOOL).run(
            SceneGenerateToolInput(
                context=AgentContext(
                    source_chunks=[
                        {
                            "type": "adaptation_direction",
                            "data": project["adaptation_direction"],
                        },
                        {
                            "type": "request",
                            "data": {**(body or {}), "shot_hints": shot_hints_enabled},
                        },
                    ],
                    upstream_artifacts={
                        "outline": outline.model_dump(mode="json"),
                        "character_voices": character_voices,
                        "author_intent": intent.model_dump(mode="json") if intent else {},
                        "non_visualizable": [
                            mark.model_dump(mode="json")
                            for mark in (
                                understanding.non_visualizable if understanding else []
                            )
                        ],
                    },
                    system_constraints={
                        "style_fingerprint": project["style_fingerprint"],
                        "voice": character_voices,
                        "author_intent": intent.model_dump(mode="json") if intent else None,
                        "shot_hints_enabled": shot_hints_enabled,
                    },
                )
            )
        )
        output = tool_output_data(result)
        data = ScreenplayData.model_validate(
            with_screenplay_defaults(
                output,
                outline,
                understanding,
                character_voices,
                shot_hints_enabled,
            )
        )
        data = data.model_copy(update={"shot_hints": ShotHints(enabled=shot_hints_enabled)})
        data = enforce_screenplay_trust(data, outline, intent, understanding)
        previous = await self.store.get_artifact(project_id, "screenplay")
        envelope = ArtifactEnvelope[ScreenplayData](
            type="screenplay",
            state=ArtifactState.DRAFT,
            parent_version=previous.version if previous else None,
            data=data,
        )
        saved = await self.store.save_artifact(project_id, envelope)
        if project["state"] == ProjectState.OUTLINED:
            await self.store.update_project_state(project_id, ProjectState.GENERATED)
        return saved.model_dump(mode="json")


def tool_output_data(result: BaseModel) -> dict[str, Any]:
    data = result.model_dump(mode="json").get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="Scene tool returned invalid data")
    return data


def with_screenplay_defaults(
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
            scene_from_outline(
                scene,
                matching_non_visualizable_marks(scene, understanding),
                character_voices,
            )
            for scene in outline.scenes
        ],
        "shot_hints": {"enabled": shot_hints_enabled},
    }


def shot_hints_enabled_from_body(body: dict | None) -> bool:
    if body is None or "shot_hints" not in body:
        return False
    return bool(body["shot_hints"])


def enforce_screenplay_trust(
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
    scenes = annotate_subtext_and_mood(scenes, outline, intent, understanding)
    scenes = backfill_dialogue_source_refs(scenes)
    scenes = ensure_must_keep_lines(scenes, intent.must_keep_lines if intent else [])
    if intent and intent.must_keep_lines:
        enforce_must_keep_lines(
            [beat for scene in scenes for beat in scene.beats],
            intent.must_keep_lines,
        )
    return data.model_copy(update={"scenes": scenes})


def annotate_subtext_and_mood(
    scenes: list[ScreenplayScene],
    outline: OutlineData,
    intent: IntentConstraints | None,
    understanding: UnderstandingData | None,
) -> list[ScreenplayScene]:
    outline_by_id = {scene.id: scene for scene in outline.scenes}
    annotated: list[ScreenplayScene] = []
    for scene in scenes:
        outline_scene = outline_by_id.get(scene.id)
        fallback_mood = scene_mood(outline_scene, intent, understanding)
        mood = style_guarded_mood(
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
                update={"subtext": beat_subtext(beat, scene, outline_scene, mood)}
            )
            for beat in scene.beats
        ]
        annotated.append(scene.model_copy(update={"mood": mood, "beats": beats}))
    return annotated


def scene_mood(
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


def style_guarded_mood(
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
    if mood_conflicts_with_style_anchor(candidate, anchor_text):
        return fallback
    return candidate


def mood_conflicts_with_style_anchor(candidate: str, anchor_text: str) -> bool:
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


def beat_subtext(
    beat: Beat,
    scene: ScreenplayScene,
    outline_scene: OutlineScene | None,
    mood: str,
) -> str:
    if beat.type in {BeatType.DIALOGUE, BeatType.VOICE_OVER, BeatType.OFF_SCREEN}:
        objective = scene.goal or (outline_scene.goal if outline_scene else None)
        return join_subtext_parts(
            [
                f"Spoken against {mood}.",
                f"Underlying intent: {objective}." if objective else None,
            ]
        )
    if beat.type == BeatType.ACTION:
        conflict = scene.conflict or (outline_scene.conflict if outline_scene else None)
        return join_subtext_parts(
            [
                f"Action carries {mood}.",
                f"Pressure point: {conflict}." if conflict else None,
            ]
        )
    if beat.type == BeatType.NOTE:
        return f"Adaptation note under {mood}."
    return f"Beat emotional state: {mood}."


def join_subtext_parts(parts: list[str | None]) -> str:
    return " ".join(part for part in parts if part)


def backfill_dialogue_source_refs(
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


def ensure_must_keep_lines(
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


def scene_from_outline(
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
        beats=beats_from_outline(scene, non_visualizable, character_voices),
    )
    return screenplay_scene.model_dump(mode="json")


def beats_from_outline(
    scene: OutlineScene,
    non_visualizable: list[NonVisualizableMark],
    character_voices: dict[str, str],
) -> list[Beat]:
    beats = [
        Beat(
            type=BeatType.ACTION,
            text=action_text(scene),
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
                parenthetical=parenthetical_for_voice(voice),
                dialogue=dialogue_text(scene, voice),
                subtext=dialogue_subtext(scene, voice),
                source_ref=scene.source_ref,
                flag=Flag.FROM_SOURCE,
            )
        )
    beats.append(
        Beat(
            type=BeatType.ACTION,
            text=ending_action(scene),
            subtext=scene.ending_state,
            source_ref=scene.source_ref,
            flag=Flag.FROM_SOURCE,
        )
    )
    for mark in non_visualizable:
        beats.append(externalization_note(scene, mark))
    return beats


def character_voices_for(characters: CharactersData | None) -> dict[str, str]:
    if characters is None:
        return {}
    return {
        character.id: character.voice
        for character in characters.characters
        if character.voice.strip()
    }


def matching_non_visualizable_marks(
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


def externalization_note(
    scene: OutlineScene,
    mark: NonVisualizableMark,
) -> Beat:
    lead_character = scene.characters[0] if scene.characters else None
    return Beat(
        type=BeatType.NOTE,
        text=f"Non-visualizable source passage requires externalization: {mark.note}",
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


def action_text(scene: OutlineScene) -> str:
    return (
        f"{scene.heading.location}. {scene.synopsis} "
        f"The scene moves through {scene.mood or 'controlled'} pressure."
    )


def dialogue_text(scene: OutlineScene, voice: str | None) -> str:
    pressure = dialogue_pressure(scene)
    if prefers_indirect_voice(voice):
        return f"You already know {pressure}."
    if prefers_clipped_voice(voice):
        return f"Enough. {pressure}."
    return f"We face it now: {pressure}."


def dialogue_pressure(scene: OutlineScene) -> str:
    if scene.conflict:
        return compact_sentence(scene.conflict)
    if scene.goal:
        return compact_sentence(scene.goal)
    return "this cannot wait"


def compact_sentence(text: str) -> str:
    cleaned = text.strip().rstrip(".")
    if len(cleaned) <= 72:
        return cleaned
    return f"{cleaned[:69].rstrip()}..."


def parenthetical_for_voice(voice: str | None) -> str | None:
    if voice is None:
        return "(plain)"
    lowered = voice.lower()
    if "quiet" in lowered or "clipped" in lowered or "restrained" in lowered:
        return "(quiet, clipped)"
    if "indirect" in lowered:
        return "(indirect)"
    return "(in character)"


def dialogue_subtext(scene: OutlineScene, voice: str | None) -> str:
    parts = []
    if scene.goal:
        parts.append(scene.goal)
    if voice:
        parts.append(f"Voice: {voice}")
    return "; ".join(parts) if parts else "Voice-constrained spoken line."


def prefers_indirect_voice(voice: str | None) -> bool:
    return voice is not None and "indirect" in voice.lower()


def prefers_clipped_voice(voice: str | None) -> bool:
    if voice is None:
        return False
    lowered = voice.lower()
    return "clipped" in lowered or "quiet" in lowered or "restrained" in lowered


def ending_action(scene: OutlineScene) -> str:
    if scene.ending_state:
        return scene.ending_state
    return "The scene lands on a clear dramatic turn."
