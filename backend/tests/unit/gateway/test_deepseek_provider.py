"""DeepSeek gateway provider tests."""

from __future__ import annotations

import pytest

from cardenio.api.errors import SchemaInvalidError
from cardenio.gateway.protocol import GenerateRequest, SystemConstraints
from cardenio.gateway.providers.deepseek import DeepSeekGateway, DeepSeekGatewayConfig


class FakeDeepSeekGateway(DeepSeekGateway):
    """Avoid network I/O while exercising payload and response parsing."""

    def __init__(self, response: dict) -> None:
        super().__init__(DeepSeekGatewayConfig(api_key="test-key"))
        self.response = response
        self.payload: dict | None = None

    def _post_json(self, payload: dict) -> dict:
        self.payload = payload
        return self.response


async def test_deepseek_gateway_builds_json_chat_request() -> None:
    gateway = FakeDeepSeekGateway(
        {
            "choices": [{"message": {"content": '{"logline":"ok"}'}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 5},
        }
    )

    result = await gateway.generate(
        GenerateRequest(
            task="understand",
            system_constraints=SystemConstraints(style_fingerprint="restrained"),
            context=[{"type": "chapter", "text": "sample"}],
            output_schema={"type": "object"},
        )
    )

    assert result.data == {"logline": "ok"}
    assert result.usage == {"input_tokens": 3, "output_tokens": 5, "latency_ms": 0}
    assert gateway.payload is not None
    assert gateway.payload["model"] == "deepseek-v4-flash"
    assert gateway.payload["response_format"] == {"type": "json_object"}
    assert gateway.payload["max_tokens"] == 8192
    assert "system_constraints.output_language" in gateway.payload["messages"][0]["content"]
    assert gateway.payload["messages"][1]["role"] == "user"
    user_content = gateway.payload["messages"][1]["content"]
    assert "understand" in user_content
    assert "style_fingerprint" in user_content


async def test_deepseek_gateway_accepts_fenced_json_content() -> None:
    gateway = FakeDeepSeekGateway(
        {"choices": [{"message": {"content": '```json\n{"ok":true}\n```'}}]}
    )

    result = await gateway.generate(
        GenerateRequest(
            task="profile",
            system_constraints=SystemConstraints(),
            context=[],
        )
    )

    assert result.data == {"ok": True}


async def test_deepseek_gateway_rejects_non_object_completion() -> None:
    gateway = FakeDeepSeekGateway({"choices": [{"message": {"content": "[]"}}]})

    with pytest.raises(SchemaInvalidError):
        await gateway.generate(
            GenerateRequest(
                task="outline",
                system_constraints=SystemConstraints(),
                context=[],
            )
        )
