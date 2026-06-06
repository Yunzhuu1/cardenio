"""Generation service — screenplay generation with scene-level fan-out (FR-7, M5)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway
    from cardenio.storage.protocol import ArtifactStore


class GenerationService:
    """Orchestrates screenplay generation: fan-out per scene, trust enforcement.

    Scene generation is the unique parallel point (agent-workflow §4.2).
    Each scene is independent; failures don't affect other scenes (NFR-6).
    """

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def generate_screenplay(
        self, project_id: str, *, scene_ids: list[str] | None = None
    ) -> dict:
        """Generate screenplay draft. Fan-out per scene (FR-7)."""
        raise NotImplementedError("GenerationService.generate_screenplay() not yet implemented")
