"""Source (novel import) API (api.md §4, API-3~6)."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile

from cardenio.domain.models.source import Chapter

router = APIRouter(prefix="/projects/{project_id}/source")


@router.post("/chapters", status_code=201)
async def create_chapter(project_id: str, chapter: Chapter) -> dict:
    """API-3: Add a chapter (paste or type)."""
    raise NotImplementedError("Chapter creation not yet implemented")


@router.post("/import")
async def import_file(project_id: str, file: UploadFile) -> dict:
    """API-4: Import TXT/DOCX file with auto-chapter detection."""
    raise NotImplementedError("File import not yet implemented")


@router.get("")
async def get_source(project_id: str) -> dict:
    """API-5: Get source material with paragraph index and threshold check."""
    raise NotImplementedError("Source retrieval not yet implemented")


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
    """API-6: Split or merge chapters (author decides)."""
    raise NotImplementedError("Chapter resegmentation not yet implemented")
