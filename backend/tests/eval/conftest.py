"""Eval fixtures: real DeepSeek gateway behind a recording wrapper.

Run with: ``uv run pytest -m eval``
Requires ``DEEPSEEK_API_KEY`` (and optionally ``DEEPSEEK_MODEL`` /
``DEEPSEEK_BASE_URL`` / ``DEEPSEEK_TIMEOUT_SECONDS`` / ``DEEPSEEK_MAX_TOKENS``).
Without an API key every eval test skips.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv
import pytest
from httpx import ASGITransport, AsyncClient

from pathlib import Path

# Load backend/.env so DEEPSEEK_API_KEY can be kept out of the conversation
# and out of git (backend/.env is gitignored).
load_dotenv(Path(__file__).resolve().parents[2] / ".env")
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from cardenio.api.app import create_app
from cardenio.gateway.protocol import GenerateRequest, GenerateResult
from cardenio.gateway.providers.deepseek import (
    DEFAULT_DEEPSEEK_BASE_URL,
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TIMEOUT_SECONDS,
    DeepSeekGateway,
    DeepSeekGatewayConfig,
)


class RecordingGateway:
    """Proxy around the real gateway that records per-call usage."""

    def __init__(self, gateway: DeepSeekGateway) -> None:
        self._gateway = gateway
        self.records: list[dict[str, Any]] = []

    async def generate(self, request: GenerateRequest) -> GenerateResult:
        result = await self._gateway.generate(request)
        self.records.append(
            {
                "task": request.task,
                "input_tokens": int(result.usage.get("input_tokens", 0)),
                "output_tokens": int(result.usage.get("output_tokens", 0)),
                "latency_ms": int(result.usage.get("latency_ms", 0)),
                "ts": datetime.now(UTC).isoformat(),
            }
        )
        return result

    @property
    def call_count(self) -> int:
        return len(self.records)

    def records_for(self, task: str) -> list[dict[str, Any]]:
        return [record for record in self.records if record["task"] == task]


def _deepseek_gateway_from_env() -> DeepSeekGateway:
    """Build a DeepSeek gateway from env, never falling back to stub."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        pytest.skip("DEEPSEEK_API_KEY not set; skipping eval")
    return DeepSeekGateway(
        DeepSeekGatewayConfig(
            api_key=api_key,
            model=os.getenv("DEEPSEEK_MODEL", DEFAULT_DEEPSEEK_MODEL),
            base_url=os.getenv("DEEPSEEK_BASE_URL", DEFAULT_DEEPSEEK_BASE_URL),
            timeout_seconds=float(
                os.getenv("DEEPSEEK_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
            ),
            max_tokens=int(os.getenv("DEEPSEEK_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
        )
    )


@pytest.fixture
def recording_gateway() -> RecordingGateway:
    """Real DeepSeek gateway wrapped with a usage recorder."""
    return RecordingGateway(_deepseek_gateway_from_env())


@pytest.fixture
async def deepseek_client(
    engine: AsyncEngine,
    recording_gateway: RecordingGateway,
) -> AsyncGenerator[tuple[AsyncClient, RecordingGateway], None]:
    """HTTP client with in-memory SQLite and the recording DeepSeek gateway."""
    app = create_app()
    app.state.engine = engine
    app.state.gateway = recording_gateway
    app.state.session_factory = async_sessionmaker(engine, expire_on_commit=False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "eval@example.com",
                "password": "correct horse battery staple",
                "display_name": "Eval User",
            },
        )
        assert auth_resp.status_code == 201
        client.headers["Authorization"] = f"Bearer {auth_resp.json()['access_token']}"
        yield client, recording_gateway
