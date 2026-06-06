"""Profile agent — character extraction (FR-3).

Produces character profiles with voice, hard_rules, relations, arc.
``voice`` and ``hard_rules`` become hard constraints for dialogue generation
once confirmed (agent-workflow §5.2).
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class ProfileAgent:
    """Extract character profiles from source (FR-3, agent-workflow §5.2)."""

    task_name = "profile"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M2
        raise NotImplementedError("ProfileAgent.run() not yet implemented")
