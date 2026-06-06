"""Schema validation + retry loop (agent-workflow §8).

The gateway validates LLM output against the expected Pydantic schema.
If validation fails, it retries with error feedback (up to N times).
If still failing, it degrades to ``needs_attention + todo`` rather than
writing bad data into the artifact store (O3).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from cardenio.gateway.protocol import LlmGateway

MAX_RETRIES = 3


class NeedsAttention:
    """Sentinel: the LLM output could not be validated after MAX_RETRIES.

    The affected unit is marked ``needs_attention`` and a ``todo`` is added
    so the author can fill it in.  This ensures bad data never pollutes
    the artifact store (agent-workflow §8).
    """

    def __init__(self, *, task: str, errors: list[str]) -> None:
        self.task = task
        self.errors = errors


async def validate_with_retry(
    raw_output: dict[str, Any],
    schema: type[BaseModel],
    gateway: LlmGateway,
    original_request: dict[str, Any],
    *,
    max_retries: int = MAX_RETRIES,
) -> BaseModel | NeedsAttention:
    """Validate LLM output against schema, retrying with error feedback.

    Implements the validate-retry loop from agent-workflow §8:
        generate → Schema validate → (fail) → retry with error → (still fail) → degrade

    Returns a validated model instance on success, or ``NeedsAttention``
    on exhausted retries.  Never raises validation errors to the caller.
    """
    errors: list[str] = []

    for attempt in range(max_retries + 1):
        try:
            return schema.model_validate(raw_output)
        except ValidationError as exc:
            errors = [f"Attempt {attempt + 1}: {err['msg']}" for err in exc.errors()]
            if attempt < max_retries:
                # Retry: feed errors back into the next LLM call
                # (full implementation will include the retry call in M2+)
                continue

    return NeedsAttention(task=original_request.get("task", "unknown"), errors=errors)
