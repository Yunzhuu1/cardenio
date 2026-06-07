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

    def __init__(self, *, max_trace_records: int = 100) -> None:
        if max_trace_records < 1:
            raise ValueError("max_trace_records must be at least 1")
        self.max_trace_records = max_trace_records
        self._traces: list[AgentRunRecord] = []

    async def run(
        self,
        *,
        agent: AgentProtocol,
        context: AgentContext,
    ) -> AgentRuntimeResult:
        result = await agent.run(context)
        runtime_result = AgentRuntimeResult.from_agent_result(
            task=agent.task_name,
            result=result,
            context=context,
        )
        self._record_trace(runtime_result.run)
        return runtime_result

    @property
    def traces(self) -> tuple[AgentRunRecord, ...]:
        """Return internal, non-content run traces in insertion order."""
        return tuple(self._traces)

    def clear_traces(self) -> None:
        """Clear internal runtime traces."""
        self._traces.clear()

    def _record_trace(self, record: AgentRunRecord | None) -> None:
        if record is None:
            return
        self._traces.append(record)
        overflow = len(self._traces) - self.max_trace_records
        if overflow > 0:
            del self._traces[:overflow]


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
