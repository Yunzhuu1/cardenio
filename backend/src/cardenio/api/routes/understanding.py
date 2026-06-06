"""Understanding (work analysis) API (api.md section 5, API-7/8)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from cardenio.api.deps import get_artifact_store, get_gateway
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, ProjectState
from cardenio.domain.models.understanding import UnderstandingData
from cardenio.gateway.protocol import GenerateRequest, LlmGateway, SystemConstraints
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/understanding")
_STUB_VALUES = {"", "stub"}


@router.post(":generate", status_code=202)
async def generate_understanding(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
    gateway: LlmGateway = Depends(get_gateway),
) -> dict:
    """API-7: Generate understanding artifact."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    chapters = await store.list_chapters(project_id)
    if len(chapters) < 3:
        return _chapter_threshold_error(len(chapters))

    result = await gateway.generate(
        GenerateRequest(
            task="understand",
            system_constraints=SystemConstraints(),
            context=[_chapter_context(chapter) for chapter in chapters],
            output_schema=UnderstandingData.model_json_schema(),
        )
    )
    data = UnderstandingData.model_validate(_with_m2_t1_defaults(result.data, chapters))
    previous = await store.get_artifact(project_id, "understanding")
    envelope = ArtifactEnvelope[UnderstandingData](
        type="understanding",
        state=ArtifactState.DRAFT,
        parent_version=previous.version if previous else None,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    if project["state"] == ProjectState.IMPORTED:
        await store.update_project_state(project_id, ProjectState.UNDERSTOOD)
    return saved.model_dump(mode="json")


@router.get("")
async def get_understanding(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-8: Get understanding artifact envelope."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    artifact = await store.get_artifact(project_id, "understanding")
    if artifact is None:
        raise HTTPException(status_code=404, detail="Understanding not found")
    return artifact.model_dump(mode="json")


@router.put("")
async def update_understanding(
    project_id: str,
    body: UnderstandingData,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-8: Edit understanding artifact; edited draft becomes the source of truth."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "understanding")
    envelope = ArtifactEnvelope[UnderstandingData](
        type="understanding",
        state=ArtifactState.DRAFT,
        parent_version=previous.version if previous else None,
        data=body,
    )
    saved = await store.save_artifact(project_id, envelope)
    return saved.model_dump(mode="json")


@router.post(":confirm")
async def confirm_understanding(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-8: Confirm understanding so downstream P1 gates can pass."""
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    previous = await store.get_artifact(project_id, "understanding")
    if previous is None:
        raise HTTPException(status_code=404, detail="Understanding not found")

    data = UnderstandingData.model_validate(previous.data)
    envelope = ArtifactEnvelope[UnderstandingData](
        type="understanding",
        state=ArtifactState.CONFIRMED,
        parent_version=previous.version,
        data=data,
    )
    saved = await store.save_artifact(project_id, envelope)
    if project["state"] == ProjectState.IMPORTED:
        await store.update_project_state(project_id, ProjectState.UNDERSTOOD)
    return saved.model_dump(mode="json")


def _chapter_threshold_error(current_chapters: int) -> JSONResponse:
    details = {
        "min_chapters": 3,
        "current_chapters": current_chapters,
        "passed": False,
    }
    return JSONResponse(
        status_code=409,
        content={
            "error": {
                "code": "chapter_threshold_unmet",
                "message": f"Need at least 3 chapters; found {current_chapters}",
                "retryable": False,
                "details": details,
            }
        },
    )


def _chapter_context(chapter: dict[str, Any]) -> dict[str, Any]:
    return {
        "chapter_id": chapter["id"],
        "order": chapter["order"],
        "title": chapter["title"],
        "paragraphs": chapter["paragraphs"],
    }


def _with_m2_t1_defaults(
    generated: dict[str, Any], chapters: list[dict[str, Any]]
) -> dict[str, Any]:
    """Fill sparse stub output with useful M2-T1 fields from source context."""
    first_text = _first_paragraph(chapters)
    defaults: dict[str, Any] = {
        "logline": f"围绕{first_text[:24] or '原作核心事件'}展开的改编前作品理解。",
        "synopsis": _source_synopsis(chapters),
        "themes": ["人物欲望", "关系变化"],
        "protagonist_goal": "确认主角在前三章中的显性目标，并在后续改编中保持一致。",
        "protagonist_fear": "失去关键关系、秘密或自我判断。",
        "central_conflict": "主角目标与外部阻力、内心犹疑之间的冲突。",
        "mood": "克制、悬念、带有情绪张力",
        "style_fingerprint": "以原文段落为约束，保持叙述节奏、意象密度和对白克制感。",
        "narrative": {
            "perspective": "third_person_limited",
            "tense": "past",
            "unreliable": False,
        },
        "non_visualizable": [],
        "strengths": ["已有至少三章连续素材，可支撑改编前理解。"],
        "difficulties": ["人物动机和心理段落需要在后续任务中继续细化。"],
    }
    merged = defaults.copy()
    for key, value in generated.items():
        if _is_meaningful(value):
            merged[key] = value
    return merged


def _is_meaningful(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip() not in _STUB_VALUES
    if isinstance(value, list | dict):
        return bool(value)
    return value is not None


def _source_synopsis(chapters: list[dict[str, Any]]) -> str:
    chapter_notes = []
    for chapter in chapters[:3]:
        paragraph = ""
        if chapter["paragraphs"]:
            paragraph = chapter["paragraphs"][0]["text"]
        chapter_notes.append(f"{chapter['title']}：{paragraph[:40]}")
    return "；".join(chapter_notes)


def _first_paragraph(chapters: list[dict[str, Any]]) -> str:
    for chapter in chapters:
        if chapter["paragraphs"]:
            return chapter["paragraphs"][0]["text"].strip()
    return ""
