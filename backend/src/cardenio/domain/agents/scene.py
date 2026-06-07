"""Scene generation agent — core screenplay generation (FR-7).

The only agent that runs in parallel (one invocation per scene, fan-out).
Produces beats with source_ref, flag, and options for non-visualizable content.
"""

from __future__ import annotations

from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext, AgentIssue, ControlledAgent
from cardenio.domain.models.screenplay import BeatType, ScreenplayData
from cardenio.gateway.protocol import LlmGateway


class SceneAgent(ControlledAgent):
    """Generate screenplay beats for a single scene (FR-7, agent-workflow §5.5)."""

    task_name = "scene"
    output_model = ScreenplayData

    def __init__(self, gateway: LlmGateway | None = None) -> None:
        self._enabled = gateway is not None
        if gateway is not None:
            super().__init__(gateway)

    async def run(self, context: AgentContext):
        if not self._enabled:
            raise NotImplementedError("SceneAgent.run() not yet implemented")
        return await super().run(context)

    def validate_domain(
        self,
        data: BaseModel,
        context: AgentContext,
    ) -> list[AgentIssue]:
        screenplay = ScreenplayData.model_validate(data)
        issues: list[AgentIssue] = []
        if not screenplay.scenes:
            issues.append(
                AgentIssue(
                    code="empty_screenplay",
                    message="at least one screenplay scene is required",
                    path="scenes",
                )
            )
            return issues

        for scene_index, scene in enumerate(screenplay.scenes):
            if not scene.id.strip():
                issues.append(
                    AgentIssue(
                        code="blank_screenplay_scene_id",
                        message="scene id must not be blank",
                        path=f"scenes.{scene_index}.id",
                    )
                )
            if not scene.source_ref.paragraphs:
                issues.append(
                    AgentIssue(
                        code="missing_scene_source_ref",
                        message="scene source_ref must include at least one paragraph",
                        path=f"scenes.{scene_index}.source_ref.paragraphs",
                    )
                )
            if not scene.beats:
                issues.append(
                    AgentIssue(
                        code="empty_scene_beats",
                        message="scene must include at least one beat",
                        path=f"scenes.{scene_index}.beats",
                    )
                )
            for beat_index, beat in enumerate(scene.beats):
                if beat.type == BeatType.TODO:
                    continue
                if beat.text is None and beat.dialogue is None:
                    issues.append(
                        AgentIssue(
                            code="blank_screenplay_beat",
                            message="non-TODO beat must include text or dialogue",
                            path=f"scenes.{scene_index}.beats.{beat_index}",
                        )
                    )
        return issues
