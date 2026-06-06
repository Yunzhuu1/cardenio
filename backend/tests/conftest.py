"""Shared test fixtures (StubLlmGateway, in-memory DB, TestClient)."""

import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from cardenio.api.app import create_app
from cardenio.gateway.protocol import LlmGateway
from cardenio.gateway.providers.stub import StubLlmGateway


@pytest.fixture
def stub_gateway() -> StubLlmGateway:
    """Stub LLM gateway that returns fixture data for testing."""
    return StubLlmGateway()


@pytest.fixture
async def app_client(stub_gateway: StubLlmGateway) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client wired with stub gateway and in-memory DB."""
    app = create_app()
    # Override gateway for testing
    app.state.gateway = stub_gateway

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client