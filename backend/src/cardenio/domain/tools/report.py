"""Internal report tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from cardenio.domain.agents.base import AgentContext
from cardenio.domain.agents.report import ReportAgent
from cardenio.domain.runtime import AgentRuntime
from cardenio.gateway.protocol import LlmGateway


class ReportGenerateToolInput(BaseModel):
    """Input for the internal report generation tool."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    context: AgentContext


class ReportGenerateToolOutput(BaseModel):
    """Output from the internal report generation tool."""

    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
    status: str
    attempts: int
    usage: dict[str, int]
    issues: list[dict[str, Any]] = []


class ReportGenerateTool:
    """Run the report agent through the internal runtime boundary."""

    name = "report.generate"
    input_model = ReportGenerateToolInput
    output_model = ReportGenerateToolOutput

    def __init__(self, *, gateway: LlmGateway, runtime: AgentRuntime) -> None:
        self.gateway = gateway
        self.runtime = runtime

    async def run(self, input_data: BaseModel) -> BaseModel:
        payload = ReportGenerateToolInput.model_validate(input_data)
        result = await self.runtime.run(
            agent=ReportAgent(self.gateway),
            context=payload.context,
        )
        return ReportGenerateToolOutput(
            data=result.data,
            status=result.status,
            attempts=result.attempts,
            usage=result.usage,
            issues=[
                {
                    "code": issue.code,
                    "message": issue.message,
                    "path": issue.path,
                    "severity": issue.severity,
                    "retryable": issue.retryable,
                }
                for issue in result.issues
            ],
        )
