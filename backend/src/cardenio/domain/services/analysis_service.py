"""Analysis service — understanding + profile orchestration (FR-2/FR-3, M2)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway
    from cardenio.storage.protocol import ArtifactStore


class AnalysisService:
    """Orchestrates understanding and character profile generation.

    Must respect confirmation gates: understanding must be confirmed
    before profile generation proceeds (P1).
    """

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def generate_understanding(self, project_id: str) -> dict:
        """Generate work understanding artifact (FR-2)."""
        raise NotImplementedError("AnalysisService.generate_understanding() not yet implemented")

    async def generate_profiles(self, project_id: str) -> dict:
        """Generate character profiles (FR-3). Requires understanding confirmed."""
        raise NotImplementedError("AnalysisService.generate_profiles() not yet implemented")
