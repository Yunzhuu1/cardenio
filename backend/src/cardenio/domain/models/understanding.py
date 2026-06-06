"""Understanding (work analysis) domain models (api.md §5, FR-2)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cardenio.domain.models.base import SourceRef


class NonVisualizableMark(BaseModel):
    """Marks a source passage that cannot be directly visualized on screen.

    FR-2.1: chapters with extended internal monologue MUST produce at
    least one ``non_visualizable`` mark (validation enforced).
    """

    model_config = ConfigDict(extra="forbid")

    source_ref: SourceRef
    note: str


class Narrative(BaseModel):
    """Narrative perspective and tense identified from source."""

    perspective: str  # e.g. "first_person", "third_person_limited", "omniscient"
    tense: str  # e.g. "past", "present"
    unreliable: bool = False


class UnderstandingData(BaseModel):
    """Understanding artifact data (api.md §5, FR-2).

    Must be confirmed by the author before downstream generation proceeds (P1).
    ``style_fingerprint`` is written into project meta as a generation constraint (NFR-2).
    """

    model_config = ConfigDict(extra="forbid")

    logline: str
    synopsis: str
    themes: list[str] = []
    protagonist_goal: str
    protagonist_fear: str
    central_conflict: str
    mood: str
    style_fingerprint: str
    narrative: Narrative
    non_visualizable: list[NonVisualizableMark] = []
    strengths: list[str] = []
    difficulties: list[str] = []
