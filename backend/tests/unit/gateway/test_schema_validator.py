"""Schema validator tests (agent-workflow §8)."""

import pytest
from pydantic import BaseModel

from cardenio.gateway.schema_validator import NeedsAttention, validate_with_retry


class SimpleModel(BaseModel):
    name: str
    value: int


async def test_valid_schema_passes() -> None:
    """Valid data should pass schema validation."""
    result = await validate_with_retry(
        raw_output={"name": "test", "value": 42},
        schema=SimpleModel,
        gateway=None,  # not needed for valid data
        original_request={"task": "test"},
    )
    assert isinstance(result, SimpleModel)
    assert result.name == "test"
    assert result.value == 42


async def test_invalid_schema_returns_needs_attention() -> None:
    """Data that fails validation after max retries returns NeedsAttention."""
    result = await validate_with_retry(
        raw_output={"invalid_field": True},  # missing required fields
        schema=SimpleModel,
        gateway=None,
        original_request={"task": "test"},
        max_retries=0,  # skip retries for this test
    )
    assert isinstance(result, NeedsAttention)
    assert result.task == "test"