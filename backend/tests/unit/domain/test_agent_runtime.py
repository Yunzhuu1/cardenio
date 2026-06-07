"""Agent runtime tests."""

from __future__ import annotations

from dataclasses import dataclass

from cardenio.domain.agents.base import AgentContext, AgentIssue, AgentResult
from cardenio.domain.runtime import AgentRuntime, summarize_context


@dataclass
class FakeAgent:
    task_name: str
    result: AgentResult
    received_context: AgentContext | None = None

    async def run(self, context: AgentContext) -> AgentResult:
        self.received_context = context
        return self.result


async def test_agent_runtime_runs_agent_and_preserves_result() -> None:
    context = AgentContext(
        source_chunks=[{"type": "chapter", "data": {"text": "source"}}],
        upstream_artifacts={"outline": {"scenes": []}},
        system_constraints={"style_fingerprint": "restrained"},
    )
    issue = AgentIssue(code="minor_warning", message="warning", severity="warning")
    agent_result = AgentResult(
        data={"ok": True},
        usage={"input_tokens": 1, "output_tokens": 2, "latency_ms": 3},
        issues=[issue],
        attempts=2,
        status="ok",
    )
    agent = FakeAgent(task_name="fake", result=agent_result)

    result = await AgentRuntime().run(agent=agent, context=context)

    assert agent.received_context is context
    assert result.data == {"ok": True}
    assert result.status == "ok"
    assert result.attempts == 2
    assert result.usage == {"input_tokens": 1, "output_tokens": 2, "latency_ms": 3}
    assert result.issues == [issue]
    assert result.run is not None
    assert result.run.task == "fake"
    assert result.run.status == "ok"
    assert result.run.attempts == 2
    assert result.run.usage == result.usage
    assert result.run.issues == [issue]
    assert result.run.context_summary == {
        "source_chunk_types": ["chapter"],
        "source_chunk_count": 1,
        "upstream_artifact_keys": ["outline"],
        "system_constraint_keys": ["style_fingerprint"],
    }


async def test_agent_runtime_preserves_needs_attention_status() -> None:
    agent = FakeAgent(
        task_name="fake",
        result=AgentResult(
            data={"needs_attention": True},
            attempts=3,
            status="needs_attention",
        ),
    )

    result = await AgentRuntime().run(agent=agent, context=AgentContext())

    assert result.status == "needs_attention"
    assert result.data == {"needs_attention": True}
    assert result.run is not None
    assert result.run.status == "needs_attention"


def test_summarize_context_omits_source_content() -> None:
    summary = summarize_context(
        AgentContext(
            source_chunks=[
                {"type": "chapter", "data": {"text": "large source text"}},
                {"data": {"text": "untyped"}},
            ],
            upstream_artifacts={"screenplay": {"scenes": [{"id": "sc_001"}]}},
            system_constraints={"voice": {"lin_wan": "quiet"}},
        )
    )

    assert summary == {
        "source_chunk_types": ["chapter", None],
        "source_chunk_count": 2,
        "upstream_artifact_keys": ["screenplay"],
        "system_constraint_keys": ["voice"],
    }
    assert "large source text" not in str(summary)
