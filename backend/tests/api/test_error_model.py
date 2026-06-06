"""Error model tests (api.md §1.6, §15.1)."""

import pytest

from cardenio.api.errors import (
    CardenioError,
    ChapterThresholdUnmetError,
    InvalidRequestError,
    LlmUnavailableError,
    NotFoundError,
    ReportFlagMismatchError,
    SchemaInvalidError,
    StateGateBlockedError,
    VersionConflictError,
    ERROR_STATUS_MAP,
)


class TestCardenioError:
    def test_to_dict_format(self) -> None:
        """Error model must match api.md §1.6 format."""
        err = CardenioError(
            code="test_error",
            message="Something went wrong",
            retryable=False,
            details={"key": "value"},
        )
        result = err.to_dict()
        assert "error" in result
        assert result["error"]["code"] == "test_error"
        assert result["error"]["message"] == "Something went wrong"
        assert result["error"]["retryable"] is False
        assert result["error"]["details"] == {"key": "value"}


class TestErrorStatusMap:
    def test_all_error_types_have_status_codes(self) -> None:
        """Every CardenioError subclass maps to an HTTP status code."""
        for err_cls in [
            InvalidRequestError,
            NotFoundError,
            VersionConflictError,
            StateGateBlockedError,
            ChapterThresholdUnmetError,
            SchemaInvalidError,
            ReportFlagMismatchError,
            LlmUnavailableError,
        ]:
            assert err_cls in ERROR_STATUS_MAP, f"{err_cls.__name__} missing from status map"

    def test_state_gate_blocked_is_409(self) -> None:
        assert ERROR_STATUS_MAP[StateGateBlockedError] == 409

    def test_schema_invalid_is_422(self) -> None:
        assert ERROR_STATUS_MAP[SchemaInvalidError] == 422

    def test_llm_unavailable_is_503(self) -> None:
        assert ERROR_STATUS_MAP[LlmUnavailableError] == 503