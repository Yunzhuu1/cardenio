"""Agent runtime for deterministic backend orchestration.

The runtime is an internal execution boundary. It does not choose the next
workflow step, expose an API, or act as an autonomous planner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from cardenio.domain.agents.base import (
    AgentContext,
    AgentIssue,
    AgentProtocol,
    AgentResult,
    AgentStatus,
)


@dataclass
class AgentRunRecord:
    """Auditable metadata for one internal agent execution."""

    task: str
    status: AgentStatus
    attempts: int
    usage: dict[str, int]
    issues: list[AgentIssue] = field(default_factory=list)
    context_summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRuntimeResult:
    """Result returned by AgentRuntime."""

    data: dict[str, Any]
    status: AgentStatus
    attempts: int
    usage: dict[str, int]
    issues: list[AgentIssue] = field(default_factory=list)
    run: AgentRunRecord | None = None

    @classmethod
    def from_agent_result(
        cls,
        *,
        task: str,
        result: AgentResult,
        context: AgentContext,
    ) -> AgentRuntimeResult:
        record = AgentRunRecord(
            task=task,
            status=result.status,
            attempts=result.attempts,
            usage=dict(result.usage),
            issues=[*result.issues],
            context_summary=summarize_context(context),
        )
        return cls(
            data=result.data,
            status=result.status,
            attempts=result.attempts,
            usage=dict(result.usage),
            issues=[*result.issues],
            run=record,
        )


class AgentRuntime:
    """Run stateless agents through one internal orchestration boundary."""

    async def run(
        self,
        *,
        agent: AgentProtocol,
        context: AgentContext,
    ) -> AgentRuntimeResult:
        result = await agent.run(context)
        return AgentRuntimeResult.from_agent_result(
            task=agent.task_name,
            result=result,
            context=context,
        )


def summarize_context(context: AgentContext) -> dict[str, Any]:
    """Return a compact, non-content summary for trace/debug records."""
    return {
        "source_chunk_types": [
            chunk.get("type")
            for chunk in context.source_chunks
            if isinstance(chunk, dict)
        ],
        "source_chunk_count": len(context.source_chunks),
        "upstream_artifact_keys": sorted(context.upstream_artifacts),
        "system_constraint_keys": sorted(context.system_constraints),
    }
