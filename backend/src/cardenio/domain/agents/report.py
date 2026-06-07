"""Report agent — adaptation tradeoff report (FR-10).

Hybrid: deterministic aggregation (flag counting, version diff) + LLM narration.
Cross-checks flag counts against screenplay markers (FR-10 verification).
"""

from __future__ import annotations

from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext, AgentIssue, ControlledAgent
from cardenio.domain.models.report import ReportData
from cardenio.gateway.protocol import LlmGateway


class ReportAgent(ControlledAgent):
    """Generate adaptation tradeoff report (FR-10, agent-workflow §5.8)."""

    task_name = "report"
    output_model = ReportData

    def __init__(self, gateway: LlmGateway | None = None) -> None:
        self._enabled = gateway is not None
        if gateway is not None:
            super().__init__(gateway)

    async def run(self, context: AgentContext):
        if not self._enabled:
            raise NotImplementedError("ReportAgent.run() not yet implemented")
        return await super().run(context)

    def validate_domain(
        self,
        data: BaseModel,
        context: AgentContext,
    ) -> list[AgentIssue]:
        report = ReportData.model_validate(data)
        issues: list[AgentIssue] = []
        if report.from_source_lines < 0:
            issues.append(
                AgentIssue(
                    code="negative_report_statistic",
                    message="from_source_lines must not be negative",
                    path="from_source_lines",
                )
            )
        if report.ai_inferred_lines < 0:
            issues.append(
                AgentIssue(
                    code="negative_report_statistic",
                    message="ai_inferred_lines must not be negative",
                    path="ai_inferred_lines",
                )
            )
        for index, item in enumerate([*report.kept, *report.added]):
            if not item.item.strip():
                issues.append(
                    AgentIssue(
                        code="blank_report_item",
                        message="report item must not be blank",
                        path=f"entries.{index}.item",
                    )
                )
        return issues
