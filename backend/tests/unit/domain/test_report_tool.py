"""Report tool tests."""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentProtocol
from cardenio.domain.runtime import AgentRuntimeResult
from cardenio.domain.tools.report import ReportGenerateTool, ReportGenerateToolInput
from cardenio.gateway.protocol import GenerateRequest, GenerateResult


class FakeGateway:
    async def generate(self, request: GenerateRequest) -> GenerateResult:
        raise AssertionError("Runtime test should not call the gateway directly")


class RecordingRuntime:
    def __init__(self) -> None:
        self.agent_task: str | None = None
        self.context: AgentContext | None = None

    async def run(
        self,
        *,
        agent: AgentProtocol,
        context: AgentContext,
    ) -> AgentRuntimeResult:
        self.agent_task = agent.task_name
        self.context = context
        return AgentRuntimeResult(
            data={"from_source_lines": 1, "ai_inferred_lines": 0},
            status="ok",
            attempts=2,
            usage={"input_tokens": 3, "output_tokens": 4, "latency_ms": 5},
        )


async def test_report_generate_tool_runs_agent_through_runtime() -> None:
    runtime = RecordingRuntime()
    context = AgentContext(
        upstream_artifacts={"screenplay": {"scenes": []}},
        system_constraints={"style_fingerprint": "restrained"},
    )
    tool = ReportGenerateTool(gateway=FakeGateway(), runtime=runtime)

    result = await tool.run(ReportGenerateToolInput(context=context))

    assert runtime.agent_task == "report"
    assert runtime.context is context
    assert result.data == {"from_source_lines": 1, "ai_inferred_lines": 0}
    assert result.status == "ok"
    assert result.attempts == 2
    assert result.usage == {"input_tokens": 3, "output_tokens": 4, "latency_ms": 5}
