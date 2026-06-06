"""Intent compile agent — deterministic form-to-constraints compilation (FR-4/FR-5).

Deterministic agent: translates author intent form into downstream hard
constraints, and checks for intent-direction conflicts (FR-5).
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class IntentCompileAgent:
    """Compile author intent into hard constraints (FR-4/FR-5, §5.3)."""

    task_name = "intent"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M3
        raise NotImplementedError("IntentCompileAgent.run() not yet implemented")
