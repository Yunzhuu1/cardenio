"""Schema and trust validation — M0-T2 core guarantee.

- Schema roundtrip: parse → edit → serialize must be lossless (FR-8.4).
- Trust enforcement: source_ref, flag, ai_inferred checks (agent-workflow §6).
"""

from cardenio.domain.validation.schema import validate_roundtrip
from cardenio.domain.validation.trust import enforce_trust

__all__ = ["validate_roundtrip", "enforce_trust"]
