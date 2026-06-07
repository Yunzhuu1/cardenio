"""LLM Gateway protocol — the stable interface between domain and LLM providers.

Business code never imports a provider SDK; it calls ``LlmGateway.generate()``
which returns validated, structured data (O2).  Switching providers only
requires a new implementation of this protocol (design.md §6.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class SystemConstraints:
    """Constraints injected by the orchestrator per agent-workflow O5.

    These are NOT suggestions — they are assembled by the context assembler
    and enforced at the orchestration level.
    """

    style_fingerprint: str | None = None
    output_language: str | None = None
    voice: dict[str, str] | None = None
    hard_rules: list[str] | None = None
    author_intent: dict[str, Any] | None = None
    shot_hints_enabled: bool = False


@dataclass
class GenerateRequest:
    """Parameters for a single LLM generation call (design.md §6.1)."""

    task: str  # understand | profile | outline | scene | rewrite | report
    system_constraints: SystemConstraints
    context: list[dict[str, Any]]  # assembled by context_assembler (O6)
    output_schema: dict[str, Any] | None = None  # expected structured output schema


@dataclass
class GenerateResult:
    """Validated output from an LLM call.

    The gateway guarantees that ``data`` has already passed schema validation
    (O2/O3).  Domain code never receives raw or invalid LLM output.
    """

    data: dict[str, Any]
    usage: dict[str, int] = field(default_factory=dict)  # input_tokens, output_tokens, latency_ms
    raw: str | None = None  # raw output for debugging


@runtime_checkable
class LlmGateway(Protocol):
    """The ONLY interface business code uses to call LLMs (design.md §6.1).

    Implementations handle:
    - Provider routing (OpenAI, Anthropic, local, etc.)
    - Structured output extraction
    - Schema validation + retry loop (agent-workflow §8)
    - Context window management
    - Caching (future)
    - Usage metering
    - Timeout and graceful degradation
    """

    async def generate(self, request: GenerateRequest) -> GenerateResult: ...
