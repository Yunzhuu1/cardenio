"""Source (novel import) domain models (api.md §4, FR-1)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SourceParagraph(BaseModel):
    """A single paragraph in the source material, indexed for traceability (P4)."""

    index: int
    text: str


class CreateChapterRequest(BaseModel):
    """Request body for creating a chapter (API-3).

    The user provides raw text; the system builds the paragraph index.
    ``id`` and ``char_count`` are generated server-side.
    """

    title: str
    text: str
    order: int = 0


class ImportChapterPreview(BaseModel):
    """Chapter preview returned by file import and accepted on confirmation."""

    title: str
    text: str
    order: int = 0


class ConfirmImportRequest(BaseModel):
    """Request body for confirming edited TXT/DOCX import preview."""

    chapters: list[ImportChapterPreview]


class Chapter(BaseModel):
    """A chapter returned by the API (api.md §4)."""

    model_config = ConfigDict(extra="forbid")

    id: str  # e.g. "ch_1", generated server-side
    title: str
    order: int
    char_count: int = 0
    paragraphs: list[SourceParagraph] = []


class SourceStats(BaseModel):
    """Aggregate stats for source threshold checking (FR-1.3)."""

    chapter_count: int
    char_count: int
    min_chapters: int = 3

    @property
    def threshold_passed(self) -> bool:
        """FR-1.3: minimum 3 chapters to proceed."""
        return self.chapter_count >= self.min_chapters
