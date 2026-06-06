"""Deterministic agent call pipeline (agent-workflow §4).

The pipeline assembles context, calls agents in order, runs trust enforcement,
and writes results.  Control flow is always deterministic (O1) — agents never
decide what happens next.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cardenio.domain.agents.base import AgentContext, AgentResult
from cardenio.gateway.protocol import LlmGateway

if TYPE_CHECKING:
    from cardenio.storage.protocol import ArtifactStore


class Pipeline:
    """Deterministic orchestration of agent calls.

    Receives a gateway and store via dependency injection.  Each method
    corresponds to a stage in the main flow (agent-workflow §4.1):
    import → understand → profile → intent → outline → generate → report.
    """

    def __init__(self, *, gateway: LlmGateway, store: ArtifactStore) -> None:
        self.gateway = gateway
        self.store = store

    async def run_agent(
        self,
        agent_task: str,
        context: AgentContext,
    ) -> AgentResult:
        """Run a single agent through the gateway and return the validated result.

        The gateway handles schema validation and retry loop (agent-workflow §8).
        """
        result = await self.gateway.generate(
            task=agent_task,
            system_constraints=context.system_constraints,
            context=context.source_chunks,
            # output_schema is resolved by the gateway based on task type
        )
        return AgentResult(data=result.data, usage=result.usage)

    # -- Stage methods (stubs, to be implemented per milestone) --

    async def run_understand(self, project_id: str) -> AgentResult:
        """understand stage: analyze source, produce understanding artifact (M2)."""
        raise NotImplementedError("Pipeline.run_understand() not yet implemented")

    async def run_profile(self, project_id: str) -> AgentResult:
        """profile stage: extract character profiles (M2)."""
        raise NotImplementedError("Pipeline.run_profile() not yet implemented")

    async def run_outline(self, project_id: str) -> AgentResult:
        """outline stage: generate scene outline (M4)."""
        raise NotImplementedError("Pipeline.run_outline() not yet implemented")

    async def run_scene(self, project_id: str, scene_id: str) -> AgentResult:
        """scene stage: generate screenplay for a single scene (M5)."""
        raise NotImplementedError("Pipeline.run_scene() not yet implemented")

    async def run_rewrite(
        self, project_id: str, scene_id: str, instruction: str
    ) -> AgentResult:
        """rewrite stage: locally rewrite a single scene (M6)."""
        raise NotImplementedError("Pipeline.run_rewrite() not yet implemented")

    async def run_report(self, project_id: str) -> AgentResult:
        """report stage: generate adaptation tradeoff report (M7)."""
        raise NotImplementedError("Pipeline.run_report() not yet implemented")
