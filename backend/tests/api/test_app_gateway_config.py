"""Application gateway configuration tests."""

from __future__ import annotations

import pytest

from cardenio.api.app import create_gateway_from_env
from cardenio.gateway.providers.deepseek import DeepSeekGateway
from cardenio.gateway.providers.stub import StubLlmGateway


def test_create_gateway_defaults_to_deepseek_with_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CARDENIO_LLM_PROVIDER", raising=False)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    gateway = create_gateway_from_env()

    assert isinstance(gateway, DeepSeekGateway)


def test_create_gateway_falls_back_to_stub_without_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CARDENIO_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    gateway = create_gateway_from_env()

    assert isinstance(gateway, StubLlmGateway)


def test_create_gateway_uses_deepseek_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CARDENIO_LLM_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://example.test")
    monkeypatch.setenv("DEEPSEEK_TIMEOUT_SECONDS", "12.5")
    monkeypatch.setenv("DEEPSEEK_MAX_TOKENS", "4096")

    gateway = create_gateway_from_env()

    assert isinstance(gateway, DeepSeekGateway)
    assert gateway.config.api_key == "test-key"
    assert gateway.config.model == "deepseek-v4-flash"
    assert gateway.config.base_url == "https://example.test"
    assert gateway.config.timeout_seconds == 12.5
    assert gateway.config.max_tokens == 4096


def test_create_gateway_falls_back_to_stub_when_deepseek_key_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CARDENIO_LLM_PROVIDER", "deepseek")
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    gateway = create_gateway_from_env()

    assert isinstance(gateway, StubLlmGateway)


def test_create_gateway_rejects_unknown_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CARDENIO_LLM_PROVIDER", "unknown")

    with pytest.raises(ValueError, match="CARDENIO_LLM_PROVIDER"):
        create_gateway_from_env()
