"""Report service — adaptation tradeoff report (FR-10, M7)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway
    from cardenio.storage.protocol import ArtifactStore


class ReportService:
    """Orchestrates adaptation tradeoff report generation (FR-10).

    Hybrid: deterministic aggregation (flag counting, version diff) + LLM narration.
    Cross-checks flag statistics against screenplay markers (FR-10 verification).
    """

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def generate_report(self, project_id: str) -> dict:
        """Generate adaptation tradeoff report. Raises if flag statistics mismatch."""
        raise NotImplementedError("ReportService.generate_report() not yet implemented")
