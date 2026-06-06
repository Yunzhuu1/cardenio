"""Usage metering for LLM calls (agent-workflow §10).

Each agent call records: task, token usage, latency, retry count, validation
failure reasons.  Used for cost observability, quality regression tracking,
and prompt iteration.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class UsageRecord:
    """A single usage record for an LLM call."""

    task: str
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0
    retry_count: int = 0
    validation_failures: list[str] = field(default_factory=list)


class UsageMeter:
    """Collects usage records for observability (agent-workflow §10)."""

    def __init__(self) -> None:
        self._records: list[UsageRecord] = []

    def record(self, usage: UsageRecord) -> None:
        self._records.append(usage)

    def summary(self) -> dict[str, dict[str, int]]:
        """Aggregate usage by task type."""
        result: dict[str, dict[str, int]] = {}
        for r in self._records:
            if r.task not in result:
                result[r.task] = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "retries": 0,
                }
            result[r.task]["calls"] += 1
            result[r.task]["input_tokens"] += r.input_tokens
            result[r.task]["output_tokens"] += r.output_tokens
            result[r.task]["retries"] += r.retry_count
        return result
