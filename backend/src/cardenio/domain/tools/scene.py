"""Internal scene generation tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from cardenio.domain.agents.base import AgentContext
from cardenio.domain.agents.scene import SceneAgent
from cardenio.domain.runtime import AgentRuntime
from cardenio.gateway.protocol import LlmGateway


class SceneGenerateToolInput(BaseModel):
    """Input for the internal scene generation tool."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    context: AgentContext


class SceneGenerateToolOutput(BaseModel):
    """Output from the internal scene generation tool."""

    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any]
    status: str
    attempts: int
    usage: dict[str, int]
    issues: list[dict[str, Any]] = []


class SceneGenerateTool:
    """Run the scene generation agent through the internal runtime boundary."""

    name = "scene.generate"
    input_model = SceneGenerateToolInput
    output_model = SceneGenerateToolOutput

    def __init__(self, *, gateway: LlmGateway, runtime: AgentRuntime) -> None:
        self.gateway = gateway
        self.runtime = runtime

    async def run(self, input_data: BaseModel) -> BaseModel:
        payload = SceneGenerateToolInput.model_validate(input_data)
        result = await self.runtime.run(
            agent=SceneAgent(self.gateway),
            context=payload.context,
        )
        return SceneGenerateToolOutput(
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
