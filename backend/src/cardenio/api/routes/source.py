"""Source (novel import) API (api.md §4, API-3~6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile

from cardenio.api.deps import get_artifact_store
from cardenio.domain.models.source import (
    Chapter,
    CreateChapterRequest,
    SourceParagraph,
    SourceStats,
)
from cardenio.storage.sqlite_store import SqliteArtifactStore

router = APIRouter(prefix="/projects/{project_id}/source")


@router.post("/chapters", status_code=201)
async def create_chapter(
    project_id: str,
    body: CreateChapterRequest,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-3: Add a chapter — persists text and builds paragraph index.

    Returns the chapter object with assigned id, order, char_count, and
    paragraph intervals for source_ref traceability (P4).
    """
    proj = await store.get_project(project_id)
    if proj is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    # Determine next chapter order
    existing = await store.list_chapters(project_id)
    order = len(existing) + 1 if not body.order else body.order

    # Split text into paragraphs
    raw_paragraphs = _split_paragraphs(body.text)

    # Persist paragraphs to build the traceability index (P4 root)
    chapter_id = f"ch_{order}"
    paragraph_models: list[SourceParagraph] = []
    for idx, para_text in enumerate(raw_paragraphs):
        paragraph_models.append(SourceParagraph(index=idx + 1, text=para_text))

    await store.save_paragraphs(
        project_id=project_id,
        chapter_id=chapter_id,
        paragraphs=[p.model_dump(mode="json") for p in paragraph_models],
    )

    return {
        "id": chapter_id,
        "title": body.title,
        "order": order,
        "char_count": sum(len(p.text) for p in paragraph_models),
        "paragraphs": [p.model_dump(mode="json") for p in paragraph_models],
    }


@router.get("")
async def get_source(
    project_id: str,
    store: SqliteArtifactStore = Depends(get_artifact_store),
) -> dict:
    """API-5: Get all chapters with paragraph index and threshold check.

    Returns chapters array and aggregate stats (FR-1.3 threshold).
    """
    proj = await store.get_project(project_id)
    if proj is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Project not found")

    chapters = await store.list_chapters(project_id)
    total_chars = sum(c["char_count"] for c in chapters)

    stats = SourceStats(chapter_count=len(chapters), char_count=total_chars)

    return {
        "chapters": chapters,
        "stats": stats.model_dump(mode="json"),
        "threshold": {
            "min_chapters": 3,
            "passed": stats.threshold_passed,
        },
    }


@router.post("/import")
async def import_file(project_id: str, file: UploadFile) -> dict:
    """API-4: Import TXT/DOCX file with auto-chapter detection. (M1-T2)"""
    raise NotImplementedError("File import not yet implemented")


@router.put("/chapters/{chapter_id}")
async def update_chapter(project_id: str, chapter_id: str, chapter: Chapter) -> dict:
    """API-6: Edit a chapter."""
    raise NotImplementedError("Chapter update not yet implemented")


@router.delete("/chapters/{chapter_id}", status_code=204)
async def delete_chapter(project_id: str, chapter_id: str) -> None:
    """API-6: Delete a chapter."""
    raise NotImplementedError("Chapter deletion not yet implemented")


@router.post("/chapters:resegment")
async def resegment_chapters(project_id: str, body: dict) -> dict:
    """API-6: Split or merge chapters (author decides). (M1-T3)"""
    raise NotImplementedError("Chapter resegmentation not yet implemented")


# -- helpers ----------------------------------------------------------------

def _split_paragraphs(text: str) -> list[str]:
    """Split text into paragraphs by double-newline.

    Single newlines within a block are preserved.
    Empty paragraphs are skipped.
    """
    blocks = text.strip().split("\n\n")
    return [b.strip() for b in blocks if b.strip()]
