"""Internal rewrite tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from cardenio.domain.agents.base import AgentContext
from cardenio.domain.agents.rewrite import RewriteAgent
from cardenio.domain.runtime import AgentRuntime
from cardenio.gateway.protocol import LlmGateway


class RewriteSceneToolInput(BaseModel):
    """Input for the internal rewrite scene tool."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    context: AgentContext


class RewriteSceneToolOutput(BaseModel):
    """Output from the internal rewrite scene tool."""

    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
    status: str
    attempts: int
    usage: dict[str, int]
    issues: list[dict[str, Any]] = []


class RewriteSceneTool:
    """Run the rewrite agent through the internal runtime boundary."""

    name = "rewrite.scene"
    input_model = RewriteSceneToolInput
    output_model = RewriteSceneToolOutput

    def __init__(self, *, gateway: LlmGateway, runtime: AgentRuntime) -> None:
        self.gateway = gateway
        self.runtime = runtime

    async def run(self, input_data: BaseModel) -> BaseModel:
        payload = RewriteSceneToolInput.model_validate(input_data)
        result = await self.runtime.run(
            agent=RewriteAgent(self.gateway),
            context=payload.context,
        )
        return RewriteSceneToolOutput(
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
