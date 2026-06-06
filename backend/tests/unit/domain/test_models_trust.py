"""Trust field validation tests (P4, P5, P6).

Verifies that source_ref, flag, and TODO enforcement logic works correctly.
"""


from cardenio.domain.models.base import Flag
from cardenio.domain.models.intent import IntentConstraints
from cardenio.domain.models.screenplay import Beat, BeatType
from cardenio.domain.validation.trust import (
    enforce_ai_inferred_flag,
    enforce_intent_gating,
    enforce_trust,
)


def test_ai_inferred_forced_on_no_source() -> None:
    """P5: beats without source_ref must be flagged ai_inferred."""
    beats = [
        Beat(type=BeatType.ACTION, text="新增的过渡动作"),
        Beat(type=BeatType.DIALOGUE, character="lin_wan", dialogue="这是AI加的台词"),
    ]
    result = enforce_ai_inferred_flag(beats, source_paragraph_indices=set())
    assert all(b.flag == Flag.AI_INFERRED for b in result)


def test_ai_inferred_not_overridden_when_exists() -> None:
    """If a beat already has from_source, it should stay."""
    beats = [
        Beat(
            type=BeatType.DIALOGUE,
            text="她说",
            source_ref={"chapter": 1, "paragraphs": [10]},
            flag=Flag.FROM_SOURCE,
            character="lin_wan",
            dialogue="原来你一直都……",
        ),
    ]
    result = enforce_ai_inferred_flag(beats, source_paragraph_indices={10})
    assert result[0].flag == Flag.FROM_SOURCE


def test_todo_beats_skip_enforcement() -> None:
    """P6: TODO beats should not be flagged as ai_inferred."""
    beats = [
        Beat(type=BeatType.TODO, text="此处需作者补充台词"),
    ]
    result = enforce_ai_inferred_flag(beats, source_paragraph_indices=set())
    # TODO beats should pass through without ai_inferred flag
    assert result[0].flag is None  # TODOs don't get flagged


def test_intent_gating_blocks_new_plot() -> None:
    """FR-4: allow_new_plot=false should reject ai_inferred plot nodes."""
    intent = IntentConstraints(allow_new_plot=False)
    beats = [
        Beat(type=BeatType.ACTION, text="新增的情节节点", flag=Flag.AI_INFERRED),
        Beat(type=BeatType.NOTE, text="外化建议", flag=Flag.AI_INFERRED),
    ]
    result = enforce_intent_gating(beats, intent)
    # ACTION beat should be converted to TODO (it's a plot node)
    assert result[0].type == BeatType.TODO
    # NOTE beat should pass through (media-translation is allowed)
    assert result[1].type == BeatType.NOTE


def test_intent_gating_allows_when_new_plot_enabled() -> None:
    """When allow_new_plot=True, ai_inferred plot nodes are allowed."""
    intent = IntentConstraints(allow_new_plot=True)
    beats = [
        Beat(type=BeatType.ACTION, text="新增的情节节点", flag=Flag.AI_INFERRED),
    ]
    result = enforce_intent_gating(beats, intent)
    assert result[0].type == BeatType.ACTION  # unchanged


def test_enforce_trust_composition() -> None:
    """enforce_trust applies all enforcement points."""
    intent = IntentConstraints(allow_new_plot=False)
    beats = [
        Beat(type=BeatType.DIALOGUE, text="没有来源的台词"),
        Beat(type=BeatType.TODO, text="留白标记"),
    ]
    result = enforce_trust(beats, source_paragraph_indices=set(), intent=intent)
    # First beat should be flagged ai_inferred, then potentially converted to TODO
    # (since it's a "plot" type dialogue without source)
    assert len(result) == 2
