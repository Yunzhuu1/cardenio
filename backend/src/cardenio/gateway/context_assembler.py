"""Context assembler — per-agent minimal context (agent-workflow §7, O6).

The assembler builds ``AgentContext`` for each agent call, including only
the necessary source chunks, upstream artifacts, and system constraints.
Never the full novel (NFR-3).
"""

from __future__ import annotations

from typing import Any

from cardenio.domain.agents.base import AgentContext
from cardenio.gateway.protocol import SystemConstraints


def assemble_context(
    task: str,
    *,
    source: dict[str, Any] | None = None,
    upstream_artifacts: dict[str, Any] | None = None,
    constraints: SystemConstraints | None = None,
) -> AgentContext:
    """Assemble minimal context for a single agent call.

    Context assembly strategy per agent (agent-workflow §7):
    - understand/profile: source by chapter chunks; orchestrator merges
    - outline: chapter chunks + understanding/character artifacts (summary level)
    - scene: ONLY the scene's source_ref paragraphs + adjacent scene summaries
      + relevant characters + intent
    - rewrite: target scene + ±1 scenes + characters + intent + user instruction
    - report: structured diff & flag statistics (mostly deterministic data)

    Full implementation per milestone.  This function provides the skeleton.
    """
    source_chunks: list[dict[str, Any]] = []
    if source and task in ("understand", "profile", "preprocess"):
        source_chunks = _chunk_source(source)

    return AgentContext(
        source_chunks=source_chunks,
        upstream_artifacts=upstream_artifacts or {},
        system_constraints=constraints and {
            "style_fingerprint": constraints.style_fingerprint,
            "voice": constraints.voice,
            "hard_rules": constraints.hard_rules,
            "author_intent": constraints.author_intent,
            "shot_hints_enabled": constraints.shot_hints_enabled,
        } or {},
    )


def _chunk_source(source: dict[str, Any]) -> list[dict[str, Any]]:
    """Split source material into chapter-level chunks (NFR-3).

    Full implementation in M1. For now, returns the source as a single chunk.
    """
    return [source]
