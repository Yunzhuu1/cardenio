"""Understanding (work analysis) API (api.md section 5, API-7/8)."""

from __future__ import annotations

import re
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
_FIRST_PERSON_MARKERS = ("我", "我们", "I ", "I'", "my ", "me ")
_THIRD_PERSON_MARKERS = ("他", "她", "他们", "她们", "he ", "she ", "they ")
_PRESENT_TENSE_MARKERS = ("正在", "此刻", "现在", "is ", "are ", "am ")
_UNRELIABLE_MARKERS = ("也许", "或许", "我不确定", "我记不清", "maybe", "perhaps")
_INTERNAL_MONOLOGUE_MARKERS = (
    "心想",
    "心里",
    "内心",
    "独白",
    "想起",
    "想象",
    "意识到",
    "明白",
    "害怕",
    "恐惧",
    "后悔",
    "记得",
    "不敢",
    "觉得",
    "thought",
    "remembered",
    "realized",
    "felt",
    "afraid",
)
_LYRICAL_MARKERS = (
    "moon",
    "rain",
    "shadow",
    "silence",
    "memory",
    "dream",
    "light",
)
_TENSE_MARKERS = ("blood", "knife", "locked", "dark", "secret", "fear", "afraid")
_HUMOR_MARKERS = ("laugh", "joke", "funny", "smile")


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
    await store.update_project_style_fingerprint(project_id, data.style_fingerprint)
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
    await store.update_project_style_fingerprint(project_id, body.style_fingerprint)
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
    await store.update_project_style_fingerprint(project_id, data.style_fingerprint)
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
        "style_fingerprint": _sample_style_fingerprint(chapters),
        "narrative": _detect_narrative(chapters),
        "non_visualizable": _detect_non_visualizable(chapters),
        "strengths": ["已有至少三章连续素材，可支撑改编前理解。"],
        "difficulties": ["人物动机和心理段落需要在后续任务中继续细化。"],
    }
    merged = defaults.copy()
    for key, value in generated.items():
        if key in {"narrative", "non_visualizable"}:
            continue
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


def _detect_narrative(chapters: list[dict[str, Any]]) -> dict[str, Any]:
    text = _all_source_text(chapters)
    lower_text = text.lower()
    first_person_count = _count_markers(text, lower_text, _FIRST_PERSON_MARKERS)
    third_person_count = _count_markers(text, lower_text, _THIRD_PERSON_MARKERS)
    perspective = (
        "first_person"
        if first_person_count > third_person_count
        else "third_person_limited"
    )
    tense = (
        "present"
        if _count_markers(text, lower_text, _PRESENT_TENSE_MARKERS) > 0
        else "past"
    )
    unreliable = _count_markers(text, lower_text, _UNRELIABLE_MARKERS) > 0
    return {
        "perspective": perspective,
        "tense": tense,
        "unreliable": unreliable,
    }


def _detect_non_visualizable(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    marks: list[dict[str, Any]] = []
    for chapter in chapters:
        chapter_order = int(chapter["order"])
        for paragraph in chapter["paragraphs"]:
            text = paragraph["text"].strip()
            if _is_non_visualizable_paragraph(text):
                marks.append(
                    {
                        "source_ref": {
                            "chapter": chapter_order,
                            "paragraphs": [int(paragraph["index"])],
                        },
                        "note": (
                            "This passage is likely internal narration or mental "
                            "state and should be externalized later instead of "
                            "being silently dropped or turned into filler dialogue."
                        ),
                    }
                )
    return marks


def _sample_style_fingerprint(chapters: list[dict[str, Any]]) -> str:
    paragraphs = [
        paragraph["text"].strip()
        for chapter in chapters
        for paragraph in chapter["paragraphs"]
        if paragraph["text"].strip()
    ]
    text = "\n".join(paragraphs)
    lower_text = text.lower()
    sentence_count = max(1, _count_sentence_endings(text))
    average_sentence_length = round(len(text) / sentence_count)
    dialogue_ratio = _dialogue_ratio(text)
    imagery_count = _count_markers(text, lower_text, _LYRICAL_MARKERS)
    tense_count = _count_markers(text, lower_text, _TENSE_MARKERS)
    humor_count = _count_markers(text, lower_text, _HUMOR_MARKERS)

    if average_sentence_length <= 45:
        cadence = "short, clipped sentences"
    else:
        cadence = "long, reflective sentences"
    dialogue = "dialogue-led" if dialogue_ratio >= 0.18 else "narration-led"
    mood = _style_mood(imagery_count, tense_count, humor_count)
    density = "image-dense" if imagery_count >= 3 else "plain-detail"

    return (
        f"{mood}; {cadence}; {dialogue}; {density}; "
        f"avg_sentence_length={average_sentence_length}; "
        f"dialogue_ratio={dialogue_ratio:.2f}"
    )


def _count_sentence_endings(text: str) -> int:
    endings = ".!?。！？"
    return sum(text.count(ending) for ending in endings)


def _dialogue_ratio(text: str) -> float:
    if not text:
        return 0.0
    dialogue_chars = sum(text.count(mark) for mark in ('"', "'", "“", "”", "「", "」"))
    return min(1.0, dialogue_chars / len(text))


def _style_mood(imagery_count: int, tense_count: int, humor_count: int) -> str:
    if humor_count >= max(2, tense_count):
        return "light, humorous"
    if tense_count >= max(2, imagery_count):
        return "tense, suspenseful"
    if imagery_count >= 2:
        return "lyrical, atmospheric"
    return "restrained, observational"


def _is_non_visualizable_paragraph(text: str) -> bool:
    lower_text = text.lower()
    marker_count = _count_markers(text, lower_text, _INTERNAL_MONOLOGUE_MARKERS)
    long_reflective = len(text) >= 80 and marker_count > 0
    dense_first_person = (
        len(text) >= 60
        and _count_markers(text, lower_text, _FIRST_PERSON_MARKERS) >= 2
        and marker_count > 0
    )
    return long_reflective or dense_first_person


def _all_source_text(chapters: list[dict[str, Any]]) -> str:
    paragraphs = []
    for chapter in chapters:
        paragraphs.extend(paragraph["text"] for paragraph in chapter["paragraphs"])
    return "\n".join(paragraphs)


def _count_markers(text: str, lower_text: str, markers: tuple[str, ...]) -> int:
    count = 0
    for marker in markers:
        if marker.isascii():
            needle = marker.strip().lower()
            count += len(re.findall(rf"\b{re.escape(needle)}\b", lower_text))
        else:
            count += text.count(marker)
    return count
