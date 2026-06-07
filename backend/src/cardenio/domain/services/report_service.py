"""Report service — adaptation tradeoff report (FR-10, M7)."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from cardenio.api.errors import ReportFlagMismatchError
from cardenio.domain.agents.base import AgentContext
from cardenio.domain.agents.report import ReportAgent
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, Flag, SourceRef
from cardenio.domain.models.report import (
    ExternalizationEntry,
    ReportData,
    ReportEntry,
    ReviewRecommendation,
)
from cardenio.domain.models.screenplay import Beat, BeatType, ScreenplayData, ScreenplayScene
from cardenio.gateway.protocol import LlmGateway
from cardenio.storage.sqlite_store import SqliteArtifactStore


class ReportService:
    """Orchestrates adaptation tradeoff report generation (FR-10).

    Hybrid: deterministic aggregation (flag counting, version diff) + LLM narration.
    Cross-checks flag statistics against screenplay markers (FR-10 verification).
    """

    def __init__(self, *, gateway: LlmGateway, store: SqliteArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def generate_report(self, project_id: str) -> dict:
        """Generate adaptation tradeoff report. Raises if flag statistics mismatch."""
        project = await self.store.get_project(project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        screenplay_artifact = await self.store.get_artifact(project_id, "screenplay")
        if screenplay_artifact is None:
            raise HTTPException(status_code=404, detail="Screenplay not found")

        screenplay = ScreenplayData.model_validate(screenplay_artifact.data)
        statistics = flag_statistics(screenplay)
        upstream_artifacts: dict[str, Any] = {
            "screenplay": screenplay_report_context(screenplay),
            "flag_statistics": statistics,
        }
        outline_artifact = await self.store.get_artifact(project_id, "outline")
        if outline_artifact is not None:
            upstream_artifacts["outline"] = outline_artifact.data
        understanding_artifact = await self.store.get_artifact(project_id, "understanding")
        if understanding_artifact is not None:
            upstream_artifacts["understanding"] = understanding_artifact.data

        agent = ReportAgent(self.gateway)
        result = await agent.run(
            AgentContext(
                upstream_artifacts=upstream_artifacts,
                system_constraints={
                    "style_fingerprint": project["style_fingerprint"],
                },
            )
        )
        data = merge_report_data(
            deterministic_report(screenplay),
            result.data,
            statistics,
        )
        envelope = ArtifactEnvelope[ReportData](
            type="report",
            state=ArtifactState.DRAFT,
            parent_version=screenplay_artifact.version,
            data=data,
        )
        saved = await self.store.save_artifact(project_id, envelope)
        return saved.model_dump(mode="json")


def deterministic_report(screenplay: ScreenplayData) -> ReportData:
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
            entry = entry_from_beat(scene, beat)
            if beat.flag == Flag.FROM_SOURCE:
                kept.append(entry)
            elif beat.flag == Flag.AI_INFERRED:
                added.append(entry)
                scene_has_review_item = True
            if is_externalized_beat(beat):
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

    statistics = flag_statistics(screenplay)
    return ReportData(
        kept=kept,
        added=added,
        externalized=externalized,
        from_source_lines=statistics["from_source_lines"],
        ai_inferred_lines=statistics["ai_inferred_lines"],
        kept_foreshadowing=kept_foreshadowing,
        review_recommended=review_recommended,
    )


def merge_report_data(
    fallback: ReportData,
    generated: dict[str, Any],
    statistics: dict[str, int],
) -> ReportData:
    if (
        not generated
        or generated.get("stub") is True
        or generated.get("needs_attention") is True
    ):
        validate_report_consistency(fallback, statistics)
        return fallback

    validate_generated_statistics(generated, statistics)
    candidate = ReportData.model_validate(
        {
            **fallback.model_dump(mode="json"),
            **generated,
            "from_source_lines": statistics["from_source_lines"],
            "ai_inferred_lines": statistics["ai_inferred_lines"],
        }
    )
    validate_report_consistency(candidate, statistics)
    return candidate


def validate_generated_statistics(
    generated: dict[str, Any],
    statistics: dict[str, int],
) -> None:
    mismatches = {
        field: {
            "expected": expected,
            "actual": generated[field],
        }
        for field, expected in statistics.items()
        if field in generated and generated[field] != expected
    }
    if mismatches:
        raise ReportFlagMismatchError(
            "Generated report statistics do not match screenplay flags",
            details={"statistics": mismatches},
        )


def validate_report_consistency(
    report: ReportData,
    statistics: dict[str, int],
) -> None:
    mismatches: dict[str, Any] = {}
    if report.from_source_lines != statistics["from_source_lines"]:
        mismatches["from_source_lines"] = {
            "expected": statistics["from_source_lines"],
            "actual": report.from_source_lines,
        }
    if report.ai_inferred_lines != statistics["ai_inferred_lines"]:
        mismatches["ai_inferred_lines"] = {
            "expected": statistics["ai_inferred_lines"],
            "actual": report.ai_inferred_lines,
        }

    added_ai_items = [
        item
        for item in report.added
        if item.flag == Flag.AI_INFERRED and (item.scene_id or item.source_ref)
    ]
    if len(added_ai_items) != statistics["ai_inferred_lines"]:
        mismatches["added"] = {
            "expected_ai_inferred_items": statistics["ai_inferred_lines"],
            "actual_ai_inferred_items": len(added_ai_items),
        }

    if mismatches:
        raise ReportFlagMismatchError(
            "Report statistics do not match screenplay flags",
            details=mismatches,
        )


def flag_statistics(screenplay: ScreenplayData) -> dict[str, int]:
    return {
        "from_source_lines": sum(
            1
            for beat in all_reportable_beats(screenplay)
            if beat.flag == Flag.FROM_SOURCE
        ),
        "ai_inferred_lines": sum(
            1
            for beat in all_reportable_beats(screenplay)
            if beat.flag == Flag.AI_INFERRED
        ),
    }


def all_reportable_beats(screenplay: ScreenplayData) -> list[Beat]:
    return [
        beat
        for scene in screenplay.scenes
        for beat in scene.beats
        if beat.type != BeatType.TODO
    ]


def entry_from_beat(scene: ScreenplayScene, beat: Beat) -> ReportEntry:
    return ReportEntry(
        item=beat_label(beat),
        source_ref=beat.source_ref or scene.source_ref,
        scene_id=scene.id,
        flag=beat.flag,
        desc=beat_desc(beat),
    )


def beat_label(beat: Beat) -> str:
    text = beat.dialogue or beat.text or beat.type.value
    if len(text) <= 96:
        return text
    return f"{text[:93].rstrip()}..."


def beat_desc(beat: Beat) -> str:
    if beat.flag == Flag.FROM_SOURCE:
        return "Kept from source material."
    if beat.flag == Flag.AI_INFERRED:
        return "Added or adapted by AI and marked for author review."
    return "Unclassified adaptation item."


def is_externalized_beat(beat: Beat) -> bool:
    if beat.type in {BeatType.VOICE_OVER, BeatType.NOTE}:
        text = (beat.text or beat.dialogue or "").lower()
        return "externalization" in text or "non-visualizable" in text
    return False


def screenplay_report_context(screenplay: ScreenplayData) -> dict[str, Any]:
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
                        "source_ref": source_ref_dump(beat.source_ref),
                        "flag": beat.flag.value if beat.flag else None,
                    }
                    for beat in scene.beats
                ],
            }
            for scene in screenplay.scenes
        ]
    }


def source_ref_dump(source_ref: SourceRef | None) -> dict[str, Any] | None:
    return source_ref.model_dump(mode="json") if source_ref else None
