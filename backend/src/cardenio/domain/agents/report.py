"""Report agent — adaptation tradeoff report (FR-10).

Hybrid: deterministic aggregation (flag counting, version diff) + LLM narration.
Cross-checks flag counts against screenplay markers (FR-10 verification).
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class ReportAgent:
    """Generate adaptation tradeoff report (FR-10, agent-workflow §5.8)."""

    task_name = "report"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M7
        raise NotImplementedError("ReportAgent.run() not yet implemented")
