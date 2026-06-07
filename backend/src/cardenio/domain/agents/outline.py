"""Outline agent — scene breakdown (FR-6).

Generates scenes with source_ref (mandatory), merge suggestions (not
auto-applied), and confirmation gates before proceeding.
"""

from __future__ import annotations

from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext, AgentIssue, ControlledAgent
from cardenio.domain.models.outline import OutlineData
from cardenio.gateway.protocol import LlmGateway


class OutlineAgent(ControlledAgent):
    """Generate scene outline from understanding + characters + intent (FR-6, §5.4)."""

    task_name = "outline"
    output_model = OutlineData

    def __init__(self, gateway: LlmGateway | None = None) -> None:
        self._enabled = gateway is not None
        if gateway is not None:
            super().__init__(gateway)

    async def run(self, context: AgentContext):
        if not self._enabled:
            raise NotImplementedError("OutlineAgent.run() not yet implemented")
        return await super().run(context)

    def validate_domain(
        self,
        data: BaseModel,
        context: AgentContext,
    ) -> list[AgentIssue]:
        outline = OutlineData.model_validate(data)
        issues: list[AgentIssue] = []
        if not outline.scenes:
            issues.append(
                AgentIssue(
                    code="empty_outline",
                    message="at least one outline scene is required",
                    path="scenes",
                )
            )
            return issues

        for index, scene in enumerate(outline.scenes):
            required_strings = {
                "id": scene.id,
                "heading.location": scene.heading.location,
                "synopsis": scene.synopsis,
            }
            for field, value in required_strings.items():
                if not value.strip():
                    issues.append(
                        AgentIssue(
                            code="blank_outline_field",
                            message=f"{field} must not be blank",
                            path=f"scenes.{index}.{field}",
                        )
                    )
            if not scene.source_ref.paragraphs:
                issues.append(
                    AgentIssue(
                        code="missing_scene_source_ref",
                        message="scene source_ref must include at least one paragraph",
                        path=f"scenes.{index}.source_ref.paragraphs",
                    )
                )
        return issues
