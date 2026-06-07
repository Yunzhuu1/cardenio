"""Rewrite service - local single-scene rewrite (FR-9.2, M6)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from pydantic import BaseModel

from cardenio.domain.context_assembler import ContextAssembler
from cardenio.domain.models.base import (
    ArtifactEnvelope,
    ArtifactState,
    Flag,
    ProjectState,
    SourceRef,
)
from cardenio.domain.models.intent import IntentConstraints
from cardenio.domain.models.screenplay import Beat, BeatType, ScreenplayData, ScreenplayScene
from cardenio.domain.runtime import AgentRuntime
from cardenio.domain.services.generation_service import (
    annotate_subtext_and_mood,
    backfill_dialogue_source_refs,
)
from cardenio.domain.tools import RewriteSceneTool, RewriteSceneToolInput, ToolRegistry
from cardenio.gateway.protocol import LlmGateway
from cardenio.orchestrator.trust_enforcer import enforce_pipeline_trust
from cardenio.storage.sqlite_store import SqliteArtifactStore

REWRITE_SCENE_TOOL = "rewrite.scene"


class RewriteService:
    """Orchestrates local rewrite of a single scene (FR-9.2)."""

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
            [RewriteSceneTool(gateway=self.gateway, runtime=self.runtime)]
        )

    async def rewrite_scene(self, project_id: str, scene_id: str, instruction: str) -> dict:
        """Locally rewrite a single scene without touching sibling scenes."""
        bundle = await ContextAssembler(store=self.store).for_rewrite(
            project_id,
            scene_id,
            instruction,
        )

        result = await self.tools.get(REWRITE_SCENE_TOOL).run(
            RewriteSceneToolInput(context=bundle.context)
        )
        output = _tool_output_data(result)

        rewritten_scene = _coerce_rewrite_result(
            output,
            bundle.target_scene,
            instruction,
        )
        rewritten_scene = _enforce_rewrite_scene_trust(
            rewritten_scene,
            bundle.target_scene,
            bundle.intent,
        )
        if bundle.outline is not None:
            rewritten_scene = annotate_subtext_and_mood(
                [rewritten_scene],
                bundle.outline,
                bundle.intent,
                bundle.understanding,
            )[0]

        scenes = [*bundle.screenplay.scenes]
        scenes[bundle.target_index] = rewritten_scene
        updated = bundle.screenplay.model_copy(update={"scenes": scenes})
        _validate_edit_trust_fields(updated)
        saved = await self._save_screenplay(project_id, updated, bundle.previous)
        await self._mark_project_editing(project_id)
        return saved.model_dump(mode="json")

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


def _tool_output_data(result: BaseModel) -> dict[str, Any]:
    data = result.model_dump(mode="json").get("data")
    if not isinstance(data, dict):
        raise HTTPException(status_code=500, detail="Rewrite tool returned invalid data")
    return data



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
