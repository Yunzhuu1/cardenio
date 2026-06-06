"""Outline agent — scene breakdown (FR-6).

Generates scenes with source_ref (mandatory), merge suggestions (not
auto-applied), and confirmation gates before proceeding.
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class OutlineAgent:
    """Generate scene outline from understanding + characters + intent (FR-6, §5.4)."""

    task_name = "outline"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M4
        raise NotImplementedError("OutlineAgent.run() not yet implemented")
