"""Export service — format rendering (FR-11, Should)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway
    from cardenio.storage.protocol import ArtifactStore


class ExportService:
    """Orchestrates export to various formats (FR-11).

    MVP priority: Fountain, DOCX, PDF.
    Renderer plugin architecture for future format support.
    """

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def export(self, project_id: str, *, format: str, version: str | None = None) -> dict:
        """Create an export job (async). Returns job info."""
        raise NotImplementedError("ExportService.export() not yet implemented")
