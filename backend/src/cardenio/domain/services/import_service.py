"""Import service — novel import and preprocessing orchestration (FR-1, design.md §4 Import)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway
    from cardenio.storage.protocol import ArtifactStore


class ImportService:
    """Orchestrates novel import: file parsing, chapter segmentation, paragraph indexing.

    M1 milestone: implement file parsing, cleaning, and threshold verification.
    """

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def import_text(self, project_id: str, text: str) -> dict:
        """Import raw text, segment into chapters, build paragraph index."""
        raise NotImplementedError("ImportService.import_text() not yet implemented")

    async def import_file(self, project_id: str, file_path: str) -> dict:
        """Import a TXT or DOCX file."""
        raise NotImplementedError("ImportService.import_file() not yet implemented")
