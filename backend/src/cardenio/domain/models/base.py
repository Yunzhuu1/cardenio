"""Foundational types shared across all domain models.

Implements PRD §7 trust fields (source_ref, flag) and api.md §2.3 artifact envelope.
These types are the structural backbone for traceability (P4) and source distinction (P5).
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Trust fields (P4 / P5 / P6) — appear on every generated artifact
# ---------------------------------------------------------------------------


class Flag(StrEnum):
    """Source distinction for beats and content elements.

    P5 / FR-7.5: Anything the AI added that is not in the source must be
    explicitly marked ``ai_inferred``; original content is ``from_source``.
    """

    FROM_SOURCE = "from_source"
    AI_INFERRED = "ai_inferred"


class SourceRef(BaseModel):
    """Traceability anchor pointing back to source material.

    P4 / FR-8.1: Every generated beat must carry ``source_ref`` locating it
    back to a chapter and paragraph range in the original novel.
    """

    chapter: int
    paragraphs: list[int]


class TrustMixin(BaseModel):
    """Mixin that injects trust fields (source_ref, flag) into beat-level models.

    Used by beat types in screenplay and outline scenes.  The orchestrator
    enforces these at write time — they are not merely prompt suggestions
    (agent-workflow §6).
    """

    source_ref: SourceRef | None = None
    flag: Flag | None = None


# ---------------------------------------------------------------------------
# Project and artifact lifecycle states
# ---------------------------------------------------------------------------


class ProjectState(StrEnum):
    """Project-level state machine (api.md §2.2).

    Transitions are strictly ordered; confirmation gates block progression
    until the author explicitly confirms the preceding artifact (P1).
    """

    EMPTY = "empty"
    IMPORTED = "imported"
    UNDERSTOOD = "understood"
    PROFILED = "profiled"
    INTENT_SET = "intent_set"
    OUTLINED = "outlined"
    GENERATED = "generated"
    EDITING = "editing"
    EXPORTED = "exported"


class ArtifactState(StrEnum):
    """Per-artifact lifecycle (api.md §2.3).

    - ``draft``      : generated but not yet confirmed by the author.
    - ``confirmed``  : author has confirmed; downstream stages may proceed.
    - ``needs_recompute`` : an upstream edit invalidated this artifact.
    """

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    NEEDS_RECOMPUTE = "needs_recompute"


# ---------------------------------------------------------------------------
# Valid project transitions (api.md §2.2)
# ---------------------------------------------------------------------------

VALID_TRANSITIONS: dict[ProjectState, set[ProjectState]] = {
    ProjectState.EMPTY: {ProjectState.IMPORTED},
    ProjectState.IMPORTED: {ProjectState.UNDERSTOOD},
    ProjectState.UNDERSTOOD: {ProjectState.PROFILED},
    ProjectState.PROFILED: {ProjectState.INTENT_SET},
    ProjectState.INTENT_SET: {ProjectState.OUTLINED},
    ProjectState.OUTLINED: {ProjectState.GENERATED},
    ProjectState.GENERATED: {ProjectState.EDITING, ProjectState.EXPORTED},
    ProjectState.EDITING: {ProjectState.GENERATED, ProjectState.EXPORTED},
    ProjectState.EXPORTED: {ProjectState.EDITING},
}

# ---------------------------------------------------------------------------
# Gate conditions: action → required artifact states (api.md §15.2)
# ---------------------------------------------------------------------------

GATE_CONDITIONS: dict[str, dict[str, ArtifactState]] = {
    "characters:generate": {"understanding": ArtifactState.CONFIRMED},
    "outline:generate": {"characters": ArtifactState.CONFIRMED},
    "screenplay:generate": {"outline": ArtifactState.CONFIRMED},
    "report:generate": {"screenplay": ArtifactState.DRAFT},
    "export": {"screenplay": ArtifactState.DRAFT},
}


# ---------------------------------------------------------------------------
# Artifact envelope (api.md §2.3)
# ---------------------------------------------------------------------------

DataT = TypeVar("DataT")


class ArtifactEnvelope[DataT](BaseModel):
    """Uniform envelope wrapping every artifact (api.md §2.3).

    All artifact GET responses share this outer structure so the API is
    consistent and the consumer always knows the lifecycle state.
    """

    model_config = ConfigDict(extra="forbid")

    type: str
    state: ArtifactState = ArtifactState.DRAFT
    version: str = Field(default_factory=lambda: f"v_{uuid4().hex[:8]}")
    parent_version: str | None = None
    etag: str | None = None
    updated_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    needs_recompute: bool = False
    data: DataT
