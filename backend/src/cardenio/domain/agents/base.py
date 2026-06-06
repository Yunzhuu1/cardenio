"""Agent base types — the contract every agent must satisfy.

Agents are stateless and idempotent (O8): the same input + constraints must
produce a reproducible output unit.  The orchestrator assembles context,
calls ``run()``, then validates and post-processes the result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class AgentContext:
    """Minimal context assembled per agent invocation (O6).

    The orchestrator builds this via ``context_assembler`` — never the full
    novel, only the slices needed for the current task.
    """

    source_chunks: list[dict[str, Any]] = field(default_factory=list)
    upstream_artifacts: dict[str, Any] = field(default_factory=dict)
    system_constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Validated output from an agent call.

    ``data`` has already passed schema validation (O2).  ``usage`` records
    tokens, latency, and retries for observability (agent-workflow §10).
    """

    data: dict[str, Any]
    usage: dict[str, int] = field(default_factory=dict)  # token counts, latency ms


@runtime_checkable
class AgentProtocol(Protocol):
    """Every agent exposes a stateless, idempotent ``run()``.

    ``task_name`` maps to the LLM gateway's ``task`` parameter so the
    orchestrator can route correctly.
    """

    task_name: str

    async def run(self, context: AgentContext) -> AgentResult: ...
