"""Output language constraint tests."""

from __future__ import annotations

from cardenio.domain.language import (
    EN_OUTPUT_RULE,
    ZH_CN_OUTPUT_RULE,
    merge_system_constraints,
    output_language_constraints,
    output_language_rule,
)


def test_output_language_constraints_default_to_simplified_chinese() -> None:
    assert output_language_constraints({}) == {
        "output_language": "zh-CN",
        "hard_rules": [ZH_CN_OUTPUT_RULE],
    }


def test_output_language_rule_preserves_english_projects() -> None:
    assert output_language_rule("en") == EN_OUTPUT_RULE
    assert output_language_rule("en-US") == EN_OUTPUT_RULE


def test_merge_system_constraints_prepends_language_rule() -> None:
    merged = merge_system_constraints(
        {
            "style_fingerprint": "restrained",
            "hard_rules": ["Keep Lin Wan quiet."],
        },
        {"output_language": "zh-CN"},
    )

    assert merged == {
        "style_fingerprint": "restrained",
        "output_language": "zh-CN",
        "hard_rules": [
            ZH_CN_OUTPUT_RULE,
            "Keep Lin Wan quiet.",
        ],
    }
