"""Output language constraints for generated artifacts."""

from __future__ import annotations

ZH_CN_OUTPUT_RULE = "All user-visible generated content must be written in Simplified Chinese."
EN_OUTPUT_RULE = "All user-visible generated content must be written in English."


def output_language_constraints(project: dict[str, object]) -> dict[str, object]:
    """Return system constraints derived from project output language."""
    output_language = str(project.get("output_language") or "zh-CN")
    return {
        "output_language": output_language,
        "hard_rules": [output_language_rule(output_language)],
    }


def merge_system_constraints(
    base: dict[str, object],
    project: dict[str, object],
) -> dict[str, object]:
    """Merge project output-language constraints into an agent context."""
    language_constraints = output_language_constraints(project)
    hard_rules = [
        *language_constraints["hard_rules"],
        *list(base.get("hard_rules") or []),
    ]
    return {
        **base,
        "output_language": language_constraints["output_language"],
        "hard_rules": hard_rules,
    }


def output_language_rule(output_language: str) -> str:
    """Map project output language to a user-visible generation rule."""
    if output_language == "zh-CN":
        return ZH_CN_OUTPUT_RULE
    if output_language.startswith("en"):
        return EN_OUTPUT_RULE
    return f"All user-visible generated content must use output language: {output_language}."
