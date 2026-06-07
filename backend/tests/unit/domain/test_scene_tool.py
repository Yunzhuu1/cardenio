"""Scene generation tool tests."""

from __future__ import annotations

from cardenio.domain.agents.base import AgentContext, AgentProtocol
from cardenio.domain.runtime import AgentRuntimeResult
from cardenio.domain.tools.scene import SceneGenerateTool, SceneGenerateToolInput
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
            data={"scenes": [], "shot_hints": {"enabled": False}},
            status="ok",
            attempts=2,
            usage={"input_tokens": 3, "output_tokens": 4, "latency_ms": 5},
        )


async def test_scene_generate_tool_runs_agent_through_runtime() -> None:
    runtime = RecordingRuntime()
    context = AgentContext(
        source_chunks=[{"type": "request", "data": {"shot_hints": False}}],
        upstream_artifacts={"outline": {"scenes": []}},
    )
    tool = SceneGenerateTool(gateway=FakeGateway(), runtime=runtime)

    result = await tool.run(SceneGenerateToolInput(context=context))

    assert runtime.agent_task == "scene"
    assert runtime.context is context
    assert result.data == {"scenes": [], "shot_hints": {"enabled": False}}
    assert result.status == "ok"
    assert result.attempts == 2
    assert result.usage == {"input_tokens": 3, "output_tokens": 4, "latency_ms": 5}
