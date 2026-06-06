"""Rewrite service — local single-scene rewrite (FR-9.2, M6)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway
    from cardenio.storage.protocol import ArtifactStore


class RewriteService:
    """Orchestrates local rewrite of a single scene (FR-9.2).

    Only the target scene is regenerated; other scenes' version pointers
    remain unchanged.  Input: target scene + instruction + adjacent context
    + characters + intent.
    """

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def rewrite_scene(self, project_id: str, scene_id: str, instruction: str) -> dict:
        """Locally rewrite a single scene (FR-9.2)."""
        raise NotImplementedError("RewriteService.rewrite_scene() not yet implemented")
