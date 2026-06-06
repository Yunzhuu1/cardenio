"""Consistency service — rename sync + conflict detection (FR-9.4, M6 Should)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway
    from cardenio.storage.protocol import ArtifactStore


class ConsistencyService:
    """Orchestrates global character rename and consistency checks (FR-9.4).

    Rename: deterministic global replacement (character id is stable).
    Conflict detection: LLM scans dialogue/actions against hard_rules.
    """

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def rename_character(self, project_id: str, character_id: str, new_name: str) -> dict:
        """Global character rename — deterministic replace of display name (FR-9.4)."""
        raise NotImplementedError("ConsistencyService.rename_character() not yet implemented")

    async def check_consistency(self, project_id: str) -> dict:
        """Check against hard_rules. Returns conflict suggestions, not auto-fixes."""
        raise NotImplementedError("ConsistencyService.check_consistency() not yet implemented")
