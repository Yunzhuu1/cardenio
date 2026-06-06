"""Pipeline tests (agent-workflow §4)."""

import pytest

from cardenio.domain.agents.base import AgentContext, AgentResult
from cardenio.gateway.protocol import GenerateRequest, SystemConstraints
from cardenio.gateway.providers.stub import StubLlmGateway
from cardenio.orchestrator.pipeline import Pipeline


@pytest.fixture
def stub_gateway() -> StubLlmGateway:
    return StubLlmGateway()


async def test_stub_gateway_returns_fixture(stub_gateway: StubLlmGateway) -> None:
    """Stub gateway returns fixture data for known task types."""
    request = GenerateRequest(
        task="understand",
        system_constraints=SystemConstraints(),
        context=[{"text": "sample"}],
    )
    result = await stub_gateway.generate(request)
    assert result.data is not None
    assert "logline" in result.data  # understand fixture has logline


async def test_stub_gateway_logs_calls(stub_gateway: StubLlmGateway) -> None:
    """Stub gateway logs all calls for test assertions."""
    request = GenerateRequest(
        task="understand",
        system_constraints=SystemConstraints(),
        context=[],
    )
    await stub_gateway.generate(request)
    assert len(stub_gateway.call_log) == 1
    assert stub_gateway.call_log[0].task == "understand"


async def test_stub_gateway_unknown_task(stub_gateway: StubLlmGateway) -> None:
    """Unknown task types return a stub placeholder."""
    request = GenerateRequest(
        task="unknown_task",
        system_constraints=SystemConstraints(),
        context=[],
    )
    result = await stub_gateway.generate(request)
    assert result.data == {"stub": True}