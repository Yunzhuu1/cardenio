"""Rewrite agent — single-scene local rewrite (FR-9.2).

Only rewrites the target scene; other scenes' versions remain untouched.
Input: target scene + instruction + adjacent context + characters + intent.
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class RewriteAgent:
    """Locally rewrite a single scene (FR-9.2, agent-workflow §5.6)."""

    task_name = "rewrite"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M6
        raise NotImplementedError("RewriteAgent.run() not yet implemented")
