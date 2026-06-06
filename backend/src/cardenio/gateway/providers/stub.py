"""Stub LLM gateway for M0 testing.

Returns minimal fixture data for each task type.  Enables end-to-end
skeleton testing without a real LLM provider.
"""

from cardenio.gateway.protocol import GenerateRequest, GenerateResult

# Minimal fixtures per task type — just enough to validate roundtrips
_MINIMAL_FIXTURES: dict[str, dict] = {
    "preprocess": {"chapters": [], "paragraph_count": 0},
    "understand": {
        "logline": "stub",
        "synopsis": "stub",
        "themes": [],
        "protagonist_goal": "stub",
        "protagonist_fear": "stub",
        "central_conflict": "stub",
        "mood": "stub",
        "style_fingerprint": "stub",
        "narrative": {"perspective": "first_person", "tense": "past", "unreliable": False},
        "non_visualizable": [],
        "strengths": [],
        "difficulties": [],
    },
    "profile": {"characters": []},
}


class StubLlmGateway:
    """Returns fixture data for testing.  Enables M0 skeleton to run
    end-to-end without a real LLM provider.
    """

    def __init__(self, fixtures: dict[str, dict] | None = None) -> None:
        self.fixtures = fixtures or _MINIMAL_FIXTURES
        self.call_log: list[GenerateRequest] = []

    async def generate(self, request: GenerateRequest) -> GenerateResult:
        self.call_log.append(request)
        key = request.task
        data = self.fixtures.get(key, {"stub": True})
        return GenerateResult(
            data=data,
            usage={"input_tokens": 100, "output_tokens": 200, "latency_ms": 500},
        )
