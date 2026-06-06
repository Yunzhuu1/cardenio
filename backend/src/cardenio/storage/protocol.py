"""Storage protocols — abstract interfaces for persistence.

These Protocols are the only storage surface that domain and orchestrator
code depends on.  Concrete implementations (SQLite, PostgreSQL, etc.) provide
the actual data access.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from cardenio.domain.models.base import ArtifactEnvelope, ProjectState


@runtime_checkable
class ArtifactStore(Protocol):
    """Persistent storage for project artifacts (design.md §5).

    Every artifact is versioned and supports optimistic concurrency via etags.
    """

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Get project metadata including state and gate status."""
        ...

    async def create_project(self, meta: dict[str, Any]) -> str:
        """Create a new project, return its ID."""
        ...

    async def update_project_state(
        self, project_id: str, state: ProjectState
    ) -> None:
        """Transition project state."""
        ...

    async def get_artifact(
        self, project_id: str, artifact_type: str
    ) -> ArtifactEnvelope | None:
        """Get the latest version of an artifact."""
        ...

    async def save_artifact(
        self, project_id: str, artifact: ArtifactEnvelope
    ) -> ArtifactEnvelope:
        """Save an artifact with a new version number."""
        ...

    async def get_source(self, project_id: str) -> dict[str, Any] | None:
        """Get source material with paragraph index."""
        ...


@runtime_checkable
class JobStore(Protocol):
    """Persistent storage for async job tracking (api.md §2.4)."""

    async def create_job(
        self, *, project_id: str, kind: str
    ) -> dict[str, Any]:
        """Create a new job record. Returns job dict with id and status."""
        ...

    async def get_job(self, job_id: str) -> dict[str, Any] | None:
        """Get job status."""
        ...

    async def update_job_status(
        self, job_id: str, status: str, error: str | None = None
    ) -> None:
        """Update job status (queued/running/succeeded/failed/canceled)."""
        ...
