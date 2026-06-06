"""Screenplay (beat-level) domain models (api.md §9, FR-7/FR-8, PRD §7)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from cardenio.domain.models.base import Flag, SourceRef
from cardenio.domain.models.outline import RelationChange, SceneHeading


class BeatType(StrEnum):
    """Types of beats within a scene (PRD §7)."""

    ACTION = "action"
    DIALOGUE = "dialogue"
    VOICE_OVER = "voice_over"
    OFF_SCREEN = "off_screen"
    NOTE = "note"
    TODO = "todo"


class BeatOption(BaseModel):
    """FR-7.1: multiple visualization options for non-visualizable content."""

    model_config = ConfigDict(extra="forbid")

    kind: str  # voice_over, action, dialogue, annotation
    text: str


class Beat(BaseModel):
    """A single beat within a scene (PRD §7).

    Trust fields (source_ref, flag) are enforced by the orchestrator,
    not merely suggested in prompts (agent-workflow §6).
    """

    model_config = ConfigDict(extra="forbid")

    type: BeatType
    text: str | None = None
    character: str | None = None  # character id for dialogue/off_screen
    parenthetical: str | None = None  # e.g. "(声音发抖)"
    dialogue: str | None = None
    subtext: str | None = None  # subtext beneath the words
    source_ref: SourceRef | None = None  # P4 mandatory for generated beats
    flag: Flag | None = None  # P5 mandatory: from_source or ai_inferred
    options: list[BeatOption] | None = None  # FR-7.1 multi-option visualization


class ShotHints(BaseModel):
    """FR-7.2: shot hints can be toggled on/off per project (NG4 default off)."""

    enabled: bool = False


class ScreenplayScene(BaseModel):
    """A single scene in the screenplay (PRD §7, api.md §9).

    Every scene must carry ``source_ref`` (FR-6.3 / FR-8.1).
    """

    model_config = ConfigDict(extra="forbid")

    id: str  # e.g. "sc_012"
    heading: SceneHeading
    source_ref: SourceRef
    synopsis: str | None = None
    goal: str | None = None
    conflict: str | None = None
    mood: str | None = None
    characters: list[str] = []
    foreshadowing: list[str] = []
    relation_changes: list[RelationChange] = []
    ending_state: str | None = None
    beats: list[Beat] = []


class ScreenplayData(BaseModel):
    """Screenplay artifact data (api.md §9)."""

    model_config = ConfigDict(extra="forbid")

    scenes: list[ScreenplayScene] = []
    shot_hints: ShotHints = ShotHints()
