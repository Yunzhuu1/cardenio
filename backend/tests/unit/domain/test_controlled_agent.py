"""Controlled agent loop tests."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from cardenio.domain.agents.base import AgentContext, AgentIssue, ControlledAgent
from cardenio.gateway.protocol import GenerateRequest, GenerateResult


class SimpleOutput(BaseModel):
    name: str
    value: int


class FakeGateway:
    def __init__(self, outputs: list[dict[str, Any]]) -> None:
        self.outputs = outputs
        self.requests: list[GenerateRequest] = []

    async def generate(self, request: GenerateRequest) -> GenerateResult:
        self.requests.append(request)
        index = len(self.requests) - 1
        return GenerateResult(
            data=self.outputs[index],
            usage={"input_tokens": 1, "output_tokens": 2, "latency_ms": 3},
        )


class SimpleAgent(ControlledAgent):
    task_name = "simple"
    output_model = SimpleOutput
    max_attempts = 3


class DomainCheckingAgent(SimpleAgent):
    def validate_domain(
        self,
        data: BaseModel,
        context: AgentContext,
    ) -> list[AgentIssue]:
        output = SimpleOutput.model_validate(data)
        if output.value < 0:
            return [
                AgentIssue(
                    code="negative_value",
                    message="value must be non-negative",
                    path="value",
                )
            ]
        return []


async def test_controlled_agent_returns_valid_output_on_first_attempt() -> None:
    gateway = FakeGateway([{"name": "ok", "value": 1}])
    agent = SimpleAgent(gateway)

    result = await agent.run(AgentContext(source_chunks=[{"type": "chapter"}]))

    assert result.status == "ok"
    assert result.attempts == 1
    assert result.data == {"name": "ok", "value": 1}
    assert result.usage == {"input_tokens": 1, "output_tokens": 2, "latency_ms": 3}
    assert result.issues == []
    assert len(gateway.requests) == 1
    assert gateway.requests[0].task == "simple"
    assert gateway.requests[0].output_schema is not None


async def test_controlled_agent_retries_with_structured_schema_issues() -> None:
    gateway = FakeGateway(
        [
            {"name": "missing value"},
            {"name": "fixed", "value": 2},
        ]
    )
    agent = SimpleAgent(gateway)

    result = await agent.run(AgentContext())

    assert result.status == "ok"
    assert result.attempts == 2
    assert result.data == {"name": "fixed", "value": 2}
    assert [issue.code for issue in result.issues] == ["schema_invalid"]
    assert result.issues[0].path == "value"
    assert len(gateway.requests) == 2
    repair_context = gateway.requests[1].context
    assert repair_context[-2]["type"] == "repair_issues"
    assert repair_context[-2]["data"][0]["code"] == "schema_invalid"
    assert repair_context[-1]["type"] == "previous_output"
    assert repair_context[-1]["data"] == {"name": "missing value"}


async def test_controlled_agent_retries_domain_issues() -> None:
    gateway = FakeGateway(
        [
            {"name": "bad", "value": -1},
            {"name": "fixed", "value": 3},
        ]
    )
    agent = DomainCheckingAgent(gateway)

    result = await agent.run(AgentContext())

    assert result.status == "ok"
    assert result.attempts == 2
    assert result.data == {"name": "fixed", "value": 3}
    assert [issue.code for issue in result.issues] == ["negative_value"]


async def test_controlled_agent_returns_fallback_after_exhausting_attempts() -> None:
    gateway = FakeGateway(
        [
            {"name": "missing value 1"},
            {"name": "missing value 2"},
            {"name": "missing value 3"},
        ]
    )
    agent = SimpleAgent(gateway)

    result = await agent.run(AgentContext())

    assert result.status == "needs_attention"
    assert result.attempts == 3
    assert result.data["needs_attention"] is True
    assert len(result.data["issues"]) == 3
    assert all(issue.code == "schema_invalid" for issue in result.issues)
    assert len(gateway.requests) == 3
