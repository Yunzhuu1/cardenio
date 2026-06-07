"""Structured error model (api.md §1.6, §15).

All non-2xx responses use this model.  Provider-specific errors are caught
at the gateway layer and converted to these domain errors — never leak
upstream (design.md §9).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CardenioError(Exception):
    """Base error for all Cardenio domain errors.

    Maps to the api.md §1.6 error model:
    ``{"error": {"code": "...", "message": "...", "retryable": bool, "details": {}}}``
    """

    code: str
    message: str
    retryable: bool = False
    details: dict | None = None

    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "details": self.details or {},
            }
        }


class InvalidRequestError(CardenioError):
    def __init__(self, message: str = "Invalid request parameters") -> None:
        super().__init__(code="invalid_request", message=message, retryable=False)


class UnauthenticatedError(CardenioError):
    def __init__(self, message: str = "Missing or invalid authentication") -> None:
        super().__init__(code="unauthenticated", message=message, retryable=False)


class ForbiddenError(CardenioError):
    def __init__(self, message: str = "You do not have access to this resource") -> None:
        super().__init__(code="forbidden", message=message, retryable=False)


class NotFoundError(CardenioError):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(code="not_found", message=message, retryable=False)


class VersionConflictError(CardenioError):
    def __init__(self, message: str = "Version conflict") -> None:
        super().__init__(code="version_conflict", message=message, retryable=False)


class StateGateBlockedError(CardenioError):
    def __init__(
        self,
        message: str = "Prerequisite confirmation gate not met",
        *,
        required_state: str = "",
        current_state: str = "",
        artifact: str = "",
    ) -> None:
        super().__init__(
            code="state_gate_blocked",
            message=message,
            retryable=False,
            details={
                "required_state": required_state,
                "current_state": current_state,
                "artifact": artifact,
            },
        )


class ChapterThresholdUnmetError(CardenioError):
    def __init__(self, message: str = "Source must have at least 3 chapters") -> None:
        super().__init__(code="chapter_threshold_unmet", message=message, retryable=False)


class SchemaInvalidError(CardenioError):
    def __init__(
        self, message: str = "Schema validation failed", details: dict | None = None
    ) -> None:
        super().__init__(code="schema_invalid", message=message, retryable=False, details=details)


class ReportFlagMismatchError(CardenioError):
    def __init__(
        self,
        message: str = "Report statistics do not match screenplay flags",
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code="report_flag_mismatch",
            message=message,
            retryable=False,
            details=details,
        )


class RateLimitedError(CardenioError):
    def __init__(self, message: str = "Rate limited, please retry later") -> None:
        super().__init__(code="rate_limited", message=message, retryable=True)


class LlmUnavailableError(CardenioError):
    def __init__(self, message: str = "LLM service unavailable") -> None:
        super().__init__(code="llm_unavailable", message=message, retryable=True)


# Mapping from CardenioError subclasses to HTTP status codes
ERROR_STATUS_MAP: dict[type[CardenioError], int] = {
    InvalidRequestError: 400,
    UnauthenticatedError: 401,
    ForbiddenError: 403,
    NotFoundError: 404,
    VersionConflictError: 409,
    StateGateBlockedError: 409,
    ChapterThresholdUnmetError: 409,
    ReportFlagMismatchError: 409,
    SchemaInvalidError: 422,
    RateLimitedError: 429,
    LlmUnavailableError: 503,
}
