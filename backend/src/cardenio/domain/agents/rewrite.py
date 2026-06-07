"""Rewrite agent — single-scene local rewrite (FR-9.2).

Only rewrites the target scene; other scenes' versions remain untouched.
Input: target scene + instruction + adjacent context + characters + intent.
"""

from __future__ import annotations

from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext, AgentIssue, ControlledAgent
from cardenio.domain.models.screenplay import BeatType, ScreenplayScene
from cardenio.gateway.protocol import LlmGateway


class RewriteAgent(ControlledAgent):
    """Locally rewrite a single scene (FR-9.2, agent-workflow §5.6)."""

    task_name = "rewrite"
    output_model = ScreenplayScene

    def __init__(self, gateway: LlmGateway | None = None) -> None:
        self._enabled = gateway is not None
        if gateway is not None:
            super().__init__(gateway)

    async def run(self, context: AgentContext):
        if not self._enabled:
            raise NotImplementedError("RewriteAgent.run() not yet implemented")
        return await super().run(context)

    def validate_domain(
        self,
        data: BaseModel,
        context: AgentContext,
    ) -> list[AgentIssue]:
        scene = ScreenplayScene.model_validate(data)
        issues: list[AgentIssue] = []
        if not scene.id.strip():
            issues.append(
                AgentIssue(
                    code="blank_rewrite_scene_id",
                    message="scene id must not be blank",
                    path="id",
                )
            )
        if not scene.source_ref.paragraphs:
            issues.append(
                AgentIssue(
                    code="missing_rewrite_source_ref",
                    message="rewritten scene source_ref must include at least one paragraph",
                    path="source_ref.paragraphs",
                )
            )
        if not scene.beats:
            issues.append(
                AgentIssue(
                    code="empty_rewrite_beats",
                    message="rewritten scene must include at least one beat",
                    path="beats",
                )
            )
        for index, beat in enumerate(scene.beats):
            if beat.type == BeatType.TODO:
                continue
            if beat.text is None and beat.dialogue is None:
                issues.append(
                    AgentIssue(
                        code="blank_rewrite_beat",
                        message="non-TODO beat must include text or dialogue",
                        path=f"beats.{index}",
                    )
                )
        return issues
