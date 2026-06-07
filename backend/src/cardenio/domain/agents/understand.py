"""Understand agent — work analysis (FR-2).

Produces the understanding artifact: logline, themes, protagonist goals,
narrative perspective, style fingerprint, non-visualizable marks, etc.
Must be confirmed by the author before downstream (P1).
"""

from __future__ import annotations

from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext, AgentIssue, ControlledAgent
from cardenio.domain.models.understanding import UnderstandingData
from cardenio.gateway.protocol import LlmGateway


class UnderstandAgent(ControlledAgent):
    """Analyze the novel for understanding (FR-2, agent-workflow §5.1)."""

    task_name = "understand"
    output_model = UnderstandingData

    def __init__(self, gateway: LlmGateway | None = None) -> None:
        self._enabled = gateway is not None
        if gateway is not None:
            super().__init__(gateway)

    async def run(self, context: AgentContext):
        if not self._enabled:
            raise NotImplementedError("UnderstandAgent.run() not yet implemented")
        return await super().run(context)

    def validate_domain(
        self,
        data: BaseModel,
        context: AgentContext,
    ) -> list[AgentIssue]:
        understanding = UnderstandingData.model_validate(data)
        issues: list[AgentIssue] = []
        required_strings = {
            "logline": understanding.logline,
            "synopsis": understanding.synopsis,
            "protagonist_goal": understanding.protagonist_goal,
            "protagonist_fear": understanding.protagonist_fear,
            "central_conflict": understanding.central_conflict,
            "mood": understanding.mood,
            "style_fingerprint": understanding.style_fingerprint,
        }
        for path, value in required_strings.items():
            if not value.strip():
                issues.append(
                    AgentIssue(
                        code="blank_understanding_field",
                        message=f"{path} must not be blank",
                        path=path,
                    )
                )
        return issues
