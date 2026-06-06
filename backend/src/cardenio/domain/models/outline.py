"""Outline (scene breakdown) domain models (api.md §8, FR-6)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from cardenio.domain.models.base import SourceRef


class IntExt(StrEnum):
    INT = "INT"
    EXT = "EXT"


class TimeOfDay(StrEnum):
    DAY = "DAY"
    NIGHT = "NIGHT"
    DAWN = "DAWN"
    DUSK = "DUSK"


class SceneHeading(BaseModel):
    """Scene heading (slug line)."""

    model_config = ConfigDict(extra="forbid")

    int_ext: IntExt
    location: str
    time: TimeOfDay


class RelationChange(BaseModel):
    """Change in character relationship within a scene."""

    model_config = ConfigDict(extra="forbid")

    characters: list[str]  # character ids
    change: str


class OutlineScene(BaseModel):
    """A single scene in the outline (FR-6).

    FR-6.3 / FR-8.1: ``source_ref`` is mandatory and must reference valid
    paragraph indices in the source material.
    """

    model_config = ConfigDict(extra="forbid")

    id: str  # e.g. "sc_012"
    heading: SceneHeading
    source_ref: SourceRef  # mandatory (FR-6.3)
    synopsis: str
    goal: str | None = None
    conflict: str | None = None
    mood: str | None = None
    characters: list[str] = []
    foreshadowing: list[str] = []
    relation_changes: list[RelationChange] = []
    ending_state: str | None = None


class MergeSuggestionStatus(StrEnum):
    PENDING = "pending"
    APPLIED = "applied"
    DISMISSED = "dismissed"


class MergeSuggestion(BaseModel):
    """FR-6.1: merges are suggestions, not automatic changes (P2)."""

    model_config = ConfigDict(extra="forbid")

    id: str
    scene_ids: list[str]
    reason: str
    status: MergeSuggestionStatus = MergeSuggestionStatus.PENDING


class OutlineData(BaseModel):
    """Outline artifact data."""

    model_config = ConfigDict(extra="forbid")

    scenes: list[OutlineScene] = []
    merge_suggestions: list[MergeSuggestion] = []
