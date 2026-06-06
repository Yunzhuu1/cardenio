"""Author intent and adaptation direction models (api.md §7, FR-4/FR-5)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class AdaptationDirection(StrEnum):
    """MVP directions: faithful, cinematic, short_drama (Must).
    Should/Could: tv, film, stage.
    """

    FAITHFUL = "faithful"
    CINEMATIC = "cinematic"
    SHORT_DRAMA = "short_drama"
    TV = "tv"
    FILM = "film"
    STAGE = "stage"


class IntentConflict(BaseModel):
    """A conflict between author intent and adaptation direction (FR-5).

    Conflicts do not block — they are presented to the author for resolution.
    """

    model_config = ConfigDict(extra="forbid")

    code: str  # e.g. "faithful_vs_new_ending"
    message: str
    fields: list[str] = []


class IntentConstraints(BaseModel):
    """Author intent compiled as downstream hard constraints (FR-4, agent-workflow §5.3).

    Intent takes priority over AI free generation (P2).
    """

    model_config = ConfigDict(extra="forbid")

    keep: list[str] = []  # content the author wants to preserve
    no_delete: list[str] = []  # plot elements that must not be deleted
    no_merge: list[str] = []  # characters that must not be merged
    must_keep_lines: list[str] = []  # exact lines that must appear verbatim
    mood_floor: str | None = None  # minimum mood (e.g. "压抑")
    allow_new_plot: bool = False  # whether AI may add new plot points
    allow_reorder: bool = False  # whether scenes may be reordered
    allow_new_ending: bool = False  # whether the ending may be changed
    target_type: AdaptationDirection | None = None
