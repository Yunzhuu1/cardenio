"""Agent base types — the contract every agent must satisfy.

Agents are stateless and idempotent (O8): the same input + constraints must
produce a reproducible output unit.  The orchestrator assembles context,
calls ``run()``, then validates and post-processes the result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ValidationError

from cardenio.gateway.protocol import GenerateRequest, LlmGateway, SystemConstraints


@dataclass
class AgentContext:
    """Minimal context assembled per agent invocation (O6).

    The orchestrator builds this via ``context_assembler`` — never the full
    novel, only the slices needed for the current task.
    """

    source_chunks: list[dict[str, Any]] = field(default_factory=list)
    upstream_artifacts: dict[str, Any] = field(default_factory=dict)
    system_constraints: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """Validated output from an agent call.

    ``data`` has already passed schema validation (O2).  ``usage`` records
    tokens, latency, and retries for observability (agent-workflow §10).
    """

    data: dict[str, Any]
    usage: dict[str, int] = field(default_factory=dict)  # token counts, latency ms
    issues: list[AgentIssue] = field(default_factory=list)
    attempts: int = 1
    status: AgentStatus = "ok"


AgentIssueSeverity = Literal["error", "warning"]
AgentStatus = Literal["ok", "needs_attention", "failed"]


@dataclass
class AgentIssue:
    """Structured diagnostic emitted by an agent run."""

    code: str
    message: str
    path: str | None = None
    severity: AgentIssueSeverity = "error"
    retryable: bool = True


@runtime_checkable
class AgentProtocol(Protocol):
    """Every agent exposes a stateless, idempotent ``run()``.

    ``task_name`` maps to the LLM gateway's ``task`` parameter so the
    orchestrator can route correctly.
    """

    task_name: str

    async def run(self, context: AgentContext) -> AgentResult: ...


class ControlledAgent:
    """Base class for bounded agent loops with validation and repair attempts."""

    task_name: str
    output_model: type[BaseModel]
    max_attempts = 3

    def __init__(self, gateway: LlmGateway) -> None:
        self.gateway = gateway

    async def run(self, context: AgentContext) -> AgentResult:
        """Run generation, validate output, and retry with structured issues."""
        issues: list[AgentIssue] = []
        usage = _empty_usage()
        request = self.build_request(context, issues=issues, previous=None)

        final_attempt = 0
        for attempt in range(1, self.max_attempts + 1):
            final_attempt = attempt
            generated = await self.gateway.generate(request)
            usage = _merge_usage(usage, generated.usage)
            parsed, parse_issues = self._parse(generated.data)
            current_issues = [*parse_issues]

            if parsed is not None:
                domain_issues = self.validate_domain(parsed, context)
                current_issues.extend(domain_issues)
                if not _has_retryable_error(current_issues):
                    return AgentResult(
                        data=parsed.model_dump(mode="json"),
                        usage=usage,
                        issues=[*issues, *current_issues],
                        attempts=attempt,
                        status="ok",
                    )

            issues.extend(current_issues)
            if attempt < self.max_attempts and _has_retryable_error(current_issues):
                request = self.build_request(
                    context,
                    issues=issues,
                    previous=generated.data,
                )
                continue

            break

        fallback = self.fallback(context, issues)
        return AgentResult(
            data=fallback,
            usage=usage,
            issues=issues,
            attempts=final_attempt,
            status="needs_attention",
        )

    def build_request(
        self,
        context: AgentContext,
        *,
        issues: list[AgentIssue],
        previous: dict[str, Any] | None,
    ) -> GenerateRequest:
        """Build a gateway request, including repair feedback after failures."""
        return GenerateRequest(
            task=self.task_name,
            system_constraints=_system_constraints_from_context(context),
            context=[
                *context.source_chunks,
                {"type": "upstream_artifacts", "data": context.upstream_artifacts},
                {"type": "repair_issues", "data": [_issue_dict(issue) for issue in issues]},
                {"type": "previous_output", "data": previous or {}},
            ],
            output_schema=self.output_model.model_json_schema(),
        )

    def validate_domain(
        self,
        data: BaseModel,
        context: AgentContext,
    ) -> list[AgentIssue]:
        """Return domain-specific issues. Subclasses can override."""
        return []

    def fallback(self, context: AgentContext, issues: list[AgentIssue]) -> dict[str, Any]:
        """Return degraded output when bounded repair attempts are exhausted."""
        return {
            "needs_attention": True,
            "issues": [_issue_dict(issue) for issue in issues],
        }

    def _parse(self, data: dict[str, Any]) -> tuple[BaseModel | None, list[AgentIssue]]:
        try:
            return self.output_model.model_validate(data), []
        except ValidationError as exc:
            return None, [_issue_from_validation_error(error) for error in exc.errors()]


def _system_constraints_from_context(context: AgentContext) -> SystemConstraints:
    constraints = context.system_constraints
    return SystemConstraints(
        style_fingerprint=constraints.get("style_fingerprint"),
        output_language=constraints.get("output_language"),
        voice=constraints.get("voice"),
        hard_rules=constraints.get("hard_rules"),
        author_intent=constraints.get("author_intent"),
        shot_hints_enabled=bool(constraints.get("shot_hints_enabled", False)),
    )


def _issue_from_validation_error(error: dict[str, Any]) -> AgentIssue:
    path = ".".join(str(part) for part in error.get("loc", ())) or None
    return AgentIssue(
        code="schema_invalid",
        message=str(error.get("msg", "Schema validation failed")),
        path=path,
        severity="error",
        retryable=True,
    )


def _issue_dict(issue: AgentIssue) -> dict[str, Any]:
    return {
        "code": issue.code,
        "message": issue.message,
        "path": issue.path,
        "severity": issue.severity,
        "retryable": issue.retryable,
    }


def _empty_usage() -> dict[str, int]:
    return {"input_tokens": 0, "output_tokens": 0, "latency_ms": 0}


def _merge_usage(left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
    return {
        "input_tokens": left.get("input_tokens", 0) + right.get("input_tokens", 0),
        "output_tokens": left.get("output_tokens", 0) + right.get("output_tokens", 0),
        "latency_ms": left.get("latency_ms", 0) + right.get("latency_ms", 0),
    }


def _has_retryable_error(issues: list[AgentIssue]) -> bool:
    return any(issue.severity == "error" and issue.retryable for issue in issues)
