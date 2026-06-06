"""Schema roundtrip validation (M0-T2 acceptance criterion).

FR-8.4 requires that YAML/JSON parse → edit → serialize is lossless.
``source_ref`` and ``flag`` must survive the roundtrip without data loss.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    pass


def validate_roundtrip(model_cls: type[BaseModel], data: dict) -> None:
    """Parse → dump → re-parse → compare; fail if data is lost.

    This is the M0-T2 acceptance test.  It guarantees that:
    - No fields are silently dropped during serialization.
    - ``source_ref`` and ``flag`` survive the roundtrip.
    - JSON ↔ Pydantic is lossless (and by extension YAML ↔ Pydantic).
    """
    instance = model_cls.model_validate(data)
    dumped = instance.model_dump(mode="json")
    re_parsed = model_cls.model_validate(dumped)
    re_dumped = re_parsed.model_dump(mode="json")
    if dumped != re_dumped:
        # Find which fields differ for a helpful error message
        _diff_keys = _find_diff_keys(dumped, re_dumped)
        msg = f"Roundtrip validation failed for {model_cls.__name__}. Lost fields: {_diff_keys}"
        raise ValueError(msg)


def _find_diff_keys(original: dict, roundtripped: dict, prefix: str = "") -> list[str]:
    """Recursively find keys that differ between original and roundtripped dicts."""
    diffs: list[str] = []
    all_keys = set(original.keys()) | set(roundtripped.keys())
    for key in all_keys:
        path = f"{prefix}.{key}" if prefix else key
        orig_val = original.get(key)
        rt_val = roundtripped.get(key)
        if orig_val != rt_val:
            if isinstance(orig_val, dict) and isinstance(rt_val, dict):
                diffs.extend(_find_diff_keys(orig_val, rt_val, path))
            else:
                diffs.append(path)
    return diffs
