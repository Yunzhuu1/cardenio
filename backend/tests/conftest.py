"""Shared test fixtures with in-memory SQLite for API integration tests."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from cardenio.api.app import create_app
from cardenio.gateway.providers.stub import StubLlmGateway
from cardenio.storage.sqlalchemy_models import Base


@pytest.fixture
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    """In-memory SQLite engine for isolated tests."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
def stub_gateway() -> StubLlmGateway:
    """Stub LLM gateway that returns fixture data for testing."""
    return StubLlmGateway()


@pytest.fixture
async def app_client(
    engine: AsyncEngine,
    stub_gateway: StubLlmGateway,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP test client with in-memory SQLite and stub gateway."""
    app = create_app()
    app.state.engine = engine
    app.state.gateway = stub_gateway
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "test@example.com",
                "password": "correct horse battery staple",
                "display_name": "Test User",
            },
        )
        assert auth_resp.status_code == 201
        client.headers["Authorization"] = f"Bearer {auth_resp.json()['access_token']}"
        yield client
