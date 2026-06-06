"""Report (adaptation tradeoff) domain models (api.md §11, FR-10)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cardenio.domain.models.base import Flag, SourceRef


class ReportEntry(BaseModel):
    """A single item in the tradeoff report."""

    model_config = ConfigDict(extra="forbid")

    item: str
    source_ref: SourceRef | None = None
    scene_id: str | None = None
    flag: Flag | None = None
    desc: str | None = None


class ExternalizationEntry(BaseModel):
    """A psychological passage that was externalized into a different medium."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    from_type: str  # e.g. "内心独白"
    to_type: str  # e.g. "voice_over"


class ReviewRecommendation(BaseModel):
    """A scene the author should review, typically because AI added content."""

    model_config = ConfigDict(extra="forbid")

    scene_id: str
    reason: str


class ReportData(BaseModel):
    """Report artifact data (api.md §11, FR-10).

    FR-10 validation: statistics ``from_source_lines`` and ``ai_inferred_lines``
    MUST match the screenplay's ``flag`` field counts.  Mismatch is a
    generation failure (FR-10 verification / FR-7.5 cross-check).
    """

    model_config = ConfigDict(extra="forbid")

    kept: list[ReportEntry] = []
    deleted: list[ReportEntry] = []
    merged: list[dict] = []  # {scene_ids: [...], into: str}
    added: list[ReportEntry] = []
    externalized: list[ExternalizationEntry] = []
    from_source_lines: int = 0
    ai_inferred_lines: int = 0
    kept_foreshadowing: list[str] = []
    review_recommended: list[ReviewRecommendation] = []
