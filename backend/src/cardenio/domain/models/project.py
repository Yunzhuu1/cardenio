"""Project-level domain models (api.md §2, §3)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from cardenio.domain.models.base import ArtifactState


class LanguageTriplet(BaseModel):
    """NFR-7: UI / Source / Output language are decoupled; no hardcoded assumptions."""

    ui_language: str = "zh-CN"
    source_language: str = "zh-CN"
    output_language: str = "zh-CN"


class GateStatus(BaseModel):
    """Maps artifact names to their confirmation status (api.md §2.2).

    Only ``confirmed`` artifacts satisfy gate checks.
    """

    understanding: ArtifactState | None = None
    characters: ArtifactState | None = None
    intent: ArtifactState | None = None
    outline: ArtifactState | None = None
    screenplay: ArtifactState | None = None


class ProjectMeta(BaseModel):
    """Project metadata (api.md §3, API-1).

    ``style_fingerprint`` is back-filled after understanding generation (NFR-2).
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    ui_language: str = "zh-CN"
    source_language: str = "zh-CN"
    output_language: str = "zh-CN"
    adaptation_direction: str | None = None
    style_fingerprint: str | None = None
