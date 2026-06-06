"""Preprocess agent — deterministic cleaning, chapter segmentation, paragraph indexing.

Agent-workflow §3: deterministic (+ lightweight LLM-assisted segmentation).
Establishes the **source paragraph index** that all downstream ``source_ref``
references point back to (P4).
"""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentResult


class PreprocessAgent:
    """Clean text, segment chapters, build paragraph index (FR-1)."""

    task_name = "preprocess"

    async def run(self, context: AgentContext) -> AgentResult:
        # TODO: implement in M1
        raise NotImplementedError("PreprocessAgent.run() not yet implemented")
