"""Source (novel import) domain models (api.md §4, FR-1)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SourceParagraph(BaseModel):
    """A single paragraph in the source material, indexed for traceability (P4)."""

    index: int
    text: str


class Chapter(BaseModel):
    """A chapter of the source novel (api.md §4, API-3/4)."""

    model_config = ConfigDict(extra="forbid")

    id: str  # e.g. "ch_1"
    title: str
    text: str
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
