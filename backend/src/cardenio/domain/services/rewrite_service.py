"""Rewrite service - local single-scene rewrite (FR-9.2, M6)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext
from cardenio.domain.agents.rewrite import RewriteAgent
from cardenio.domain.models.base import (
    ArtifactEnvelope,
    ArtifactState,
    Flag,
    ProjectState,
    SourceRef,
)
from cardenio.domain.models.characters import CharactersData
from cardenio.domain.models.intent import IntentConstraints
from cardenio.domain.models.outline import OutlineData
from cardenio.domain.models.screenplay import Beat, BeatType, ScreenplayData, ScreenplayScene
from cardenio.domain.models.understanding import UnderstandingData
from cardenio.domain.services.generation_service import (
    annotate_subtext_and_mood,
    backfill_dialogue_source_refs,
    character_voices_for,
)
from cardenio.gateway.protocol import LlmGateway
from cardenio.orchestrator.trust_enforcer import enforce_pipeline_trust
from cardenio.storage.sqlite_store import SqliteArtifactStore


class RewriteService:
    """Orchestrates local rewrite of a single scene (FR-9.2)."""

    def __init__(self, *, gateway: LlmGateway, store: SqliteArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def rewrite_scene(self, project_id: str, scene_id: str, instruction: str) -> dict:
        """Locally rewrite a single scene without touching sibling scenes."""
        previous, data = await self._get_screenplay_data(project_id)
        project = await self.store.get_project(project_id)
        target_index = _find_scene_index(data, scene_id)
        target_scene = data.scenes[target_index]
        characters = await self._get_optional_artifact(
            project_id, "characters", CharactersData
        )
        intent = await self._get_optional_artifact(project_id, "intent", IntentConstraints)
        understanding = await self._get_optional_artifact(
            project_id, "understanding", UnderstandingData
        )
        outline = await self._get_optional_artifact(project_id, "outline", OutlineData)
        character_voices = character_voices_for(characters)
        source_paragraphs = await self._resolve_source_ref(
            project_id, target_scene.source_ref
        )

        result = await RewriteAgent(self.gateway).run(
            AgentContext(
                source_chunks=[
                    {
                        "type": "rewrite_request",
                        "data": {
                            "instruction": instruction,
                            "scene_id": scene_id,
                        },
                    }
                ],
                upstream_artifacts={
                    "target_scene": target_scene.model_dump(mode="json"),
                    "adjacent_scenes": _adjacent_scene_context(
                        data.scenes,
                        target_index,
                    ),
                    "source_paragraphs": source_paragraphs,
                    "character_voices": character_voices,
                    "author_intent": intent.model_dump(mode="json") if intent else {},
                    "understanding": understanding.model_dump(mode="json")
                    if understanding
                    else {},
                },
                system_constraints={
                    "style_fingerprint": project["style_fingerprint"]
                    if project
                    else None,
                    "voice": character_voices,
                    "author_intent": intent.model_dump(mode="json") if intent else None,
                    "shot_hints_enabled": data.shot_hints.enabled,
                },
            )
        )

        rewritten_scene = _coerce_rewrite_result(
            result.data,
            target_scene,
            instruction,
        )
        rewritten_scene = _enforce_rewrite_scene_trust(
            rewritten_scene,
            target_scene,
            intent,
        )
        if outline is not None:
            rewritten_scene = annotate_subtext_and_mood(
                [rewritten_scene],
                outline,
                intent,
                understanding,
            )[0]

        scenes = [*data.scenes]
        scenes[target_index] = rewritten_scene
        updated = data.model_copy(update={"scenes": scenes})
        _validate_edit_trust_fields(updated)
        saved = await self._save_screenplay(project_id, updated, previous)
        await self._mark_project_editing(project_id)
        return saved.model_dump(mode="json")

    async def _get_screenplay_data(
        self,
        project_id: str,
    ) -> tuple[ArtifactEnvelope[Any], ScreenplayData]:
        project = await self.store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        artifact = await self.store.get_artifact(project_id, "screenplay")
        if artifact is None:
            raise HTTPException(status_code=404, detail="Screenplay not found")
        return artifact, ScreenplayData.model_validate(artifact.data)

    async def _save_screenplay(
        self,
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
        return await self.store.save_artifact(project_id, envelope)

    async def _mark_project_editing(self, project_id: str) -> None:
        project = await self.store.get_project(project_id)
        if project is not None and project["state"] != ProjectState.EDITING:
            await self.store.update_project_state(project_id, ProjectState.EDITING)

    async def _get_optional_artifact(
        self,
        project_id: str,
        artifact_type: str,
        model: type[BaseModel],
    ) -> Any | None:
        artifact = await self.store.get_artifact(project_id, artifact_type)
        if artifact is None:
            return None
        return model.model_validate(artifact.data)

    async def _resolve_source_ref(
        self,
        project_id: str,
        source_ref: SourceRef,
    ) -> list[dict[str, Any]]:
        chapter_id = f"ch_{source_ref.chapter}"
        rows = await self.store.get_paragraphs(project_id, chapter_id=chapter_id)
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
    if not generated or generated.get("stub") is True or generated.get("needs_attention"):
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
    return backfill_dialogue_source_refs([enforced])[0]


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
