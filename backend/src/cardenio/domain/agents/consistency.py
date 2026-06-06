"""Consistency agent — global rename + conflict detection (FR-9.4).

Hybrid: deterministic rename sync + LLM-powered conflict detection against
hard_rules.
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class ConsistencyAgent:
    """Check character consistency and perform global renames (FR-9.4, §5.7)."""

    task_name = "consistency"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M6
        raise NotImplementedError("ConsistencyAgent.run() not yet implemented")
