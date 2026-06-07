"""Internal context assembly for stage agents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext
from cardenio.domain.models.base import ArtifactEnvelope, SourceRef
from cardenio.domain.models.characters import CharactersData
from cardenio.domain.models.intent import IntentConstraints
from cardenio.domain.models.outline import OutlineData
from cardenio.domain.models.screenplay import ScreenplayData, ScreenplayScene
from cardenio.domain.models.understanding import UnderstandingData
from cardenio.domain.services.generation_service import character_voices_for
from cardenio.storage.sqlite_store import SqliteArtifactStore


@dataclass(frozen=True)
class RewriteContextBundle:
    """Data needed to run and persist a single-scene rewrite."""

    context: AgentContext
    previous: ArtifactEnvelope[Any]
    screenplay: ScreenplayData
    target_index: int
    target_scene: ScreenplayScene
    intent: IntentConstraints | None
    understanding: UnderstandingData | None
    outline: OutlineData | None
    input_versions: dict[str, str]


class ContextAssembler:
    """Builds internal agent context from stored project artifacts."""

    def __init__(self, *, store: SqliteArtifactStore) -> None:
        self.store = store

    async def for_rewrite(
        self,
        project_id: str,
        scene_id: str,
        instruction: str,
    ) -> RewriteContextBundle:
        """Assemble the complete agent context for local scene rewrite."""
        project = await self.store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        previous = await self.store.get_artifact(project_id, "screenplay")
        if previous is None:
            raise HTTPException(status_code=404, detail="Screenplay not found")

        screenplay = ScreenplayData.model_validate(previous.data)
        target_index = _find_scene_index(screenplay, scene_id)
        target_scene = screenplay.scenes[target_index]

        characters_envelope, characters = await self._get_optional_artifact(
            project_id,
            "characters",
            CharactersData,
        )
        intent_envelope, intent = await self._get_optional_artifact(
            project_id,
            "intent",
            IntentConstraints,
        )
        understanding_envelope, understanding = await self._get_optional_artifact(
            project_id,
            "understanding",
            UnderstandingData,
        )
        outline_envelope, outline = await self._get_optional_artifact(
            project_id,
            "outline",
            OutlineData,
        )
        character_voices = character_voices_for(characters)
        source_paragraphs = await self._resolve_source_ref(
            project_id,
            target_scene.source_ref,
        )

        input_versions = {"screenplay": previous.version}
        for artifact_type, envelope in (
            ("characters", characters_envelope),
            ("intent", intent_envelope),
            ("understanding", understanding_envelope),
            ("outline", outline_envelope),
        ):
            if envelope is not None:
                input_versions[artifact_type] = envelope.version

        context = AgentContext(
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
                    screenplay.scenes,
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
                "style_fingerprint": project["style_fingerprint"],
                "voice": character_voices,
                "author_intent": intent.model_dump(mode="json") if intent else None,
                "shot_hints_enabled": screenplay.shot_hints.enabled,
            },
        )

        return RewriteContextBundle(
            context=context,
            previous=previous,
            screenplay=screenplay,
            target_index=target_index,
            target_scene=target_scene,
            intent=intent,
            understanding=understanding,
            outline=outline,
            input_versions=input_versions,
        )

    async def _get_optional_artifact(
        self,
        project_id: str,
        artifact_type: str,
        model: type[BaseModel],
    ) -> tuple[ArtifactEnvelope[Any] | None, Any | None]:
        artifact = await self.store.get_artifact(project_id, artifact_type)
        if artifact is None:
            return None, None
        return artifact, model.model_validate(artifact.data)

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
