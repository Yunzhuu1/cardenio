"""DeepSeek OpenAI-compatible LLM gateway."""

from __future__ import annotations

import asyncio
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from cardenio.api.errors import LlmUnavailableError, SchemaInvalidError
from cardenio.gateway.protocol import GenerateRequest, GenerateResult

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_TOKENS = 8192


@dataclass(frozen=True)
class DeepSeekGatewayConfig:
    """Runtime configuration for DeepSeek chat completions."""

    api_key: str
    model: str = DEFAULT_DEEPSEEK_MODEL
    base_url: str = DEFAULT_DEEPSEEK_BASE_URL
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_tokens: int = DEFAULT_MAX_TOKENS


class DeepSeekGateway:
    """OpenAI-compatible gateway for DeepSeek chat completions."""

    def __init__(self, config: DeepSeekGatewayConfig) -> None:
        if not config.api_key.strip():
            raise ValueError("DeepSeek API key must not be blank")
        self.config = config

    async def generate(self, request: GenerateRequest) -> GenerateResult:
        payload = self._build_payload(request)
        response = await asyncio.to_thread(self._post_json, payload)
        return self._parse_response(response)

    def _build_payload(self, request: GenerateRequest) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Cardenio's structured adaptation assistant. "
                        "Return only valid JSON that matches the requested schema. "
                        "Do not wrap the JSON in markdown."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": request.task,
                            "system_constraints": _jsonable(request.system_constraints),
                            "context": request.context,
                            "output_schema": request.output_schema,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": self.config.max_tokens,
        }

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(
                request, timeout=self.config.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise LlmUnavailableError(
                f"DeepSeek API returned HTTP {exc.code}: {details}"
            ) from exc
        except OSError as exc:
            raise LlmUnavailableError(f"DeepSeek API request failed: {exc}") from exc

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SchemaInvalidError(
                "DeepSeek API returned non-JSON response",
                details={"raw": raw[:500]},
            ) from exc
        if not isinstance(parsed, dict):
            raise SchemaInvalidError("DeepSeek API response must be a JSON object")
        return parsed

    def _parse_response(self, response: dict[str, Any]) -> GenerateResult:
        try:
            choice = response["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise SchemaInvalidError(
                "DeepSeek API response is missing chat completion content",
                details={"response": response},
            ) from exc

        if not isinstance(content, str) or not content.strip():
            raise SchemaInvalidError("DeepSeek API returned empty completion content")

        try:
            data = json.loads(_strip_json_fence(content))
        except json.JSONDecodeError as exc:
            raise SchemaInvalidError(
                "DeepSeek completion content is not valid JSON",
                details={"content": content[:500]},
            ) from exc
        if not isinstance(data, dict):
            raise SchemaInvalidError("DeepSeek completion JSON must be an object")

        usage = response.get("usage") or {}
        return GenerateResult(
            data=data,
            usage={
                "input_tokens": int(usage.get("prompt_tokens", 0)),
                "output_tokens": int(usage.get("completion_tokens", 0)),
                "latency_ms": 0,
            },
            raw=content,
        )


def _jsonable(value: Any) -> Any:
    if hasattr(value, "__dict__"):
        return value.__dict__
    return value


def _strip_json_fence(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped
