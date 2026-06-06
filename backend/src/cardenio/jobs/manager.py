"""Job lifecycle manager (api.md §2.4).

Jobs track long-running LLM operations (understand, profile, outline,
screenplay generation, report).  Status transitions:
    queued → running → succeeded | failed
    queued → canceled
"""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.storage.protocol import JobStore


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class JobManager:
    """Manages job lifecycle: create, run, complete, fail, cancel."""

    def __init__(self, store: JobStore) -> None:
        self.store = store

    async def create(self, *, project_id: str, kind: str) -> dict:
        """Create a new job record."""
        return await self.store.create_job(project_id=project_id, kind=kind)

    async def start(self, job_id: str) -> None:
        """Transition job from queued to running."""
        await self.store.update_job_status(job_id, JobStatus.RUNNING.value)

    async def succeed(self, job_id: str) -> None:
        """Transition job to succeeded."""
        await self.store.update_job_status(job_id, JobStatus.SUCCEEDED.value)

    async def fail(self, job_id: str, error: str) -> None:
        """Transition job to failed with error message."""
        await self.store.update_job_status(
            job_id, JobStatus.FAILED.value, error=error
        )

    async def cancel(self, job_id: str) -> None:
        """Transition job to canceled."""
        await self.store.update_job_status(job_id, JobStatus.CANCELED.value)
