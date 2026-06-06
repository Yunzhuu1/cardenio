"""Understand agent — work analysis (FR-2).

Produces the understanding artifact: logline, themes, protagonist goals,
narrative perspective, style fingerprint, non-visualizable marks, etc.
Must be confirmed by the author before downstream (P1).
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class UnderstandAgent:
    """Analyze the novel for understanding (FR-2, agent-workflow §5.1)."""

    task_name = "understand"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M2
        raise NotImplementedError("UnderstandAgent.run() not yet implemented")
