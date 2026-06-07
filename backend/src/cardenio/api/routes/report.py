"""Report (adaptation tradeoff) API (api.md §11, API-25/26)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, Flag, SourceRef
from cardenio.domain.models.report import (
    ExternalizationEntry,
    ReportData,
    ReportEntry,
    ReviewRecommendation,
)
from cardenio.domain.models.screenplay import Beat, BeatType, ScreenplayData, ScreenplayScene
from cardenio.gateway.protocol import GenerateRequest, LlmGateway, SystemConstraints
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/report")


@router.post(":generate", status_code=202)
async def generate_report(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-25: Generate adaptation tradeoff report (async Job).

    Gate: screenplay must exist.
    Cross-check: report statistics must match screenplay flag counts (FR-10).
    """
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    screenplay_artifact = await store.get_artifact(project_id, "screenplay")
    if screenplay_artifact is None:
        raise HTTPException(status_code=404, detail="Screenplay not found")

    screenplay = ScreenplayData.model_validate(screenplay_artifact.data)
    statistics = _flag_statistics(screenplay)
    context = [
        {"type": "screenplay", "data": _screenplay_report_context(screenplay)},
        {"type": "flag_statistics", "data": statistics},
    ]
    outline_artifact = await store.get_artifact(project_id, "outline")
    if outline_artifact is not None:
        context.append({"type": "outline", "data": outline_artifact.data})
    understanding_artifact = await store.get_artifact(project_id, "understanding")
    if understanding_artifact is not None:
        context.append({"type": "understanding", "data": understanding_artifact.data})

    generated = await gateway.generate(
        GenerateRequest(
            task="report",
            system_constraints=SystemConstraints(
                style_fingerprint=project["style_fingerprint"],
            ),
            context=context,
            output_schema=ReportData.model_json_schema(),
        )
    )
    data = _merge_report_data(
        _deterministic_report(screenplay),
        generated.data,
        statistics,
    )
    envelope = ArtifactEnvelope[ReportData](
        type="report",
        state=ArtifactState.DRAFT,
        parent_version=screenplay_artifact.version,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    return saved.model_dump(mode="json")


@router.get("")
async def get_report(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-26: Get the report artifact envelope."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "report")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return artifact.model_dump(mode="json")


def _deterministic_report(screenplay: ScreenplayData) -> ReportData:
    kept: list[ReportEntry] = []
    added: list[ReportEntry] = []
    externalized: list[ExternalizationEntry] = []
    review_recommended: list[ReviewRecommendation] = []
    kept_foreshadowing: list[str] = []

    for scene in screenplay.scenes:
        kept_foreshadowing.extend(scene.foreshadowing)
        scene_has_review_item = False
        for beat in scene.beats:
            if beat.type == BeatType.TODO:
                scene_has_review_item = True
                continue
            entry = _entry_from_beat(scene, beat)
            if beat.flag == Flag.FROM_SOURCE:
                kept.append(entry)
            elif beat.flag == Flag.AI_INFERRED:
                added.append(entry)
                scene_has_review_item = True
            if _is_externalized_beat(beat):
                externalized.append(
                    ExternalizationEntry(
                        scene_id=scene.id,
                        from_type="non_visualizable_source",
                        to_type=beat.type.value,
                    )
                )
        if scene_has_review_item:
            review_recommended.append(
                ReviewRecommendation(
                    scene_id=scene.id,
                    reason="Scene contains AI-inferred or TODO material.",
                )
            )

    statistics = _flag_statistics(screenplay)
    return ReportData(
        kept=kept,
        added=added,
        externalized=externalized,
        from_source_lines=statistics["from_source_lines"],
        ai_inferred_lines=statistics["ai_inferred_lines"],
        kept_foreshadowing=kept_foreshadowing,
        review_recommended=review_recommended,
    )


def _merge_report_data(
    fallback: ReportData,
    generated: dict[str, Any],
    statistics: dict[str, int],
) -> ReportData:
    if not generated or generated.get("stub") is True:
        return fallback

    candidate = ReportData.model_validate(
        {
            **fallback.model_dump(mode="json"),
            **generated,
            "from_source_lines": statistics["from_source_lines"],
            "ai_inferred_lines": statistics["ai_inferred_lines"],
        }
    )
    return candidate


def _flag_statistics(screenplay: ScreenplayData) -> dict[str, int]:
    return {
        "from_source_lines": sum(
            1
            for beat in _all_reportable_beats(screenplay)
            if beat.flag == Flag.FROM_SOURCE
        ),
        "ai_inferred_lines": sum(
            1
            for beat in _all_reportable_beats(screenplay)
            if beat.flag == Flag.AI_INFERRED
        ),
    }


def _all_reportable_beats(screenplay: ScreenplayData) -> list[Beat]:
    return [
        beat
        for scene in screenplay.scenes
        for beat in scene.beats
        if beat.type != BeatType.TODO
    ]


def _entry_from_beat(scene: ScreenplayScene, beat: Beat) -> ReportEntry:
    return ReportEntry(
        item=_beat_label(beat),
        source_ref=beat.source_ref or scene.source_ref,
        scene_id=scene.id,
        flag=beat.flag,
        desc=_beat_desc(beat),
    )


def _beat_label(beat: Beat) -> str:
    text = beat.dialogue or beat.text or beat.type.value
    if len(text) <= 96:
        return text
    return f"{text[:93].rstrip()}..."


def _beat_desc(beat: Beat) -> str:
    if beat.flag == Flag.FROM_SOURCE:
        return "Kept from source material."
    if beat.flag == Flag.AI_INFERRED:
        return "Added or adapted by AI and marked for author review."
    return "Unclassified adaptation item."


def _is_externalized_beat(beat: Beat) -> bool:
    if beat.type in {BeatType.VOICE_OVER, BeatType.NOTE}:
        text = (beat.text or beat.dialogue or "").lower()
        return "externalization" in text or "non-visualizable" in text
    return False


def _screenplay_report_context(screenplay: ScreenplayData) -> dict[str, Any]:
    return {
        "scenes": [
            {
                "id": scene.id,
                "source_ref": scene.source_ref.model_dump(mode="json"),
                "synopsis": scene.synopsis,
                "beats": [
                    {
                        "type": beat.type.value,
                        "text": beat.dialogue or beat.text,
                        "source_ref": _source_ref_dump(beat.source_ref),
                        "flag": beat.flag.value if beat.flag else None,
                    }
                    for beat in scene.beats
                ],
            }
            for scene in screenplay.scenes
        ]
    }


def _source_ref_dump(source_ref: SourceRef | None) -> dict[str, Any] | None:
    return source_ref.model_dump(mode="json") if source_ref else None
