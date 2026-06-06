"""Scene generation agent — core screenplay generation (FR-7).

The only agent that runs in parallel (one invocation per scene, fan-out).
Produces beats with source_ref, flag, and options for non-visualizable content.
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class SceneAgent:
    """Generate screenplay beats for a single scene (FR-7, agent-workflow §5.5)."""

    task_name = "scene"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M5
        raise NotImplementedError("SceneAgent.run() not yet implemented")
