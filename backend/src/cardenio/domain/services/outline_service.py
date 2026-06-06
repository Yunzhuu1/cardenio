"""Outline service — scene breakdown generation (FR-6, M4)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway
    from cardenio.storage.protocol import ArtifactStore


class OutlineService:
    """Orchestrates outline generation with merge suggestions (FR-6)."""

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def generate_outline(self, project_id: str) -> dict:
        """Generate scene outline from understanding + characters + intent."""
        raise NotImplementedError("OutlineService.generate_outline() not yet implemented")
