"""M0-T2 acceptance: Pydantic model roundtrip tests.

FR-8.4 requires that YAML/JSON parse → edit → serialize is lossless.
``source_ref`` and ``flag`` must survive the roundtrip without data loss.
"""

import pytest

from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState, Flag, SourceRef
from cardenio.domain.models.screenplay import (
    Beat,
    BeatOption,
    BeatType,
    ScreenplayData,
    ScreenplayScene,
    ShotHints,
)
from cardenio.domain.models.outline import IntExt, SceneHeading, TimeOfDay
from cardenio.domain.models.understanding import UnderstandingData, Narrative, NonVisualizableMark
from cardenio.domain.models.characters import Character, CharacterRole, CharactersData
from cardenio.domain.models.intent import AdaptationDirection, IntentConstraints
from cardenio.domain.models.report import ReportData
from cardenio.domain.validation.schema import validate_roundtrip


# --- Screenplay roundtrip (PRD §7 full example) ---

SCREENPLAY_DATA = {
    "scenes": [
        {
            "id": "sc_012",
            "heading": {"int_ext": "INT", "location": "旧书店", "time": "NIGHT"},
            "source_ref": {"chapter": 2, "paragraphs": [45, 51]},
            "synopsis": "林晚发现父亲的信",
            "goal": "揭示父亲秘密",
            "conflict": "真相与逃避的撕扯",
            "mood": "压抑、悬而未决",
            "characters": ["lin_wan", "lin_fu"],
            "foreshadowing": ["父亲的怀表"],
            "relation_changes": [
                {"characters": ["lin_wan", "lin_fu"], "change": "信任出现裂缝"}
            ],
            "ending_state": "林晚握紧日记，决定追查",
            "beats": [
                {
                    "type": "action",
                    "text": "林晚拂去书脊的灰，抽出一本日记。",
                    "subtext": "她其实早就知道它在这里。",
                    "source_ref": {"chapter": 2, "paragraphs": [46]},
                    "flag": "from_source",
                },
                {
                    "type": "dialogue",
                    "character": "lin_wan",
                    "parenthetical": "(声音发抖)",
                    "dialogue": "原来你一直都……",
                    "source_ref": {"chapter": 2, "paragraphs": [48]},
                    "flag": "from_source",
                },
                {
                    "type": "note",
                    "text": "原文为大段内心独白，建议用画外音处理，可替换为动作。",
                    "flag": "ai_inferred",
                    "options": [
                        {"kind": "voice_over", "text": "（V.O.）这一次，我不会再回头。"},
                        {"kind": "action", "text": "林晚合上日记，吹熄了灯。"},
                    ],
                },
                {
                    "type": "todo",
                    "text": "此处需作者补充父女对峙的关键台词。",
                },
            ],
        }
    ],
    "shot_hints": {"enabled": False},
}


def test_screenplay_roundtrip() -> None:
    """Screenplay data must survive parse → dump → re-parse losslessly."""
    validate_roundtrip(ScreenplayData, SCREENPLAY_DATA)


def test_screenplay_source_ref_survives() -> None:
    """source_ref and flag must not be lost (FR-8.4, P4, P5)."""
    scene = ScreenplayData.model_validate(SCREENPLAY_DATA)
    # The action beat has source_ref and flag
    action_beat = scene.scenes[0].beats[0]
    assert action_beat.source_ref is not None
    assert action_beat.source_ref.chapter == 2
    assert action_beat.source_ref.paragraphs == [46]
    assert action_beat.flag == Flag.FROM_SOURCE

    # Roundtrip preserves them
    dumped = scene.model_dump(mode="json")
    re_parsed = ScreenplayData.model_validate(dumped)
    re_beat = re_parsed.scenes[0].beats[0]
    assert re_beat.source_ref is not None
    assert re_beat.source_ref.chapter == 2
    assert re_beat.flag == Flag.FROM_SOURCE


def test_beat_types_valid() -> None:
    """All beat types from PRD §7 are valid."""
    for bt in BeatType:
        BeatType(bt.value)  # should not raise


def test_ai_inferred_flag_preserved() -> None:
    """ai_inferred flag must roundtrip (P5 compliance)."""
    scene = ScreenplayData.model_validate(SCREENPLAY_DATA)
    note_beat = scene.scenes[0].beats[2]  # the note with ai_inferred
    assert note_beat.flag == Flag.AI_INFERRED

    dumped = scene.model_dump(mode="json")
    re_parsed = ScreenplayData.model_validate(dumped)
    re_note = re_parsed.scenes[0].beats[2]
    assert re_note.flag == Flag.AI_INFERRED


# --- Understanding roundtrip ---

UNDERSTANDING_DATA = {
    "logline": "一个女孩在父亲的旧书店里追查他的死亡真相。",
    "synopsis": "讲述林晚的故事",
    "themes": ["记忆与和解"],
    "protagonist_goal": "找回父亲的真相",
    "protagonist_fear": "再次被抛弃",
    "central_conflict": "真相与逃避的撕扯",
    "mood": "压抑、悬而未决",
    "style_fingerprint": "克制、冷硬、意象密集",
    "narrative": {"perspective": "first_person", "tense": "past", "unreliable": False},
    "non_visualizable": [
        {
            "source_ref": {"chapter": 1, "paragraphs": [12, 18]},
            "note": "大段内心独白，需外化",
        }
    ],
    "strengths": ["意象集中"],
    "difficulties": ["心理戏多"],
}


def test_understanding_roundtrip() -> None:
    validate_roundtrip(UnderstandingData, UNDERSTANDING_DATA)


# --- Characters roundtrip ---

CHARACTERS_DATA = {
    "characters": [
        {
            "id": "lin_wan",
            "name": "林晚",
            "role": "protagonist",
            "voice": "克制、爱用反问",
            "desire": "找回父亲的真相",
            "fear": "再次被抛弃",
            "arc": "从回避到直面",
            "relations": [{"to": "lin_fu", "type": "父女", "change": "由疏离到和解"}],
            "hard_rules": ["从不主动示弱"],
        }
    ]
}


def test_characters_roundtrip() -> None:
    validate_roundtrip(CharactersData, CHARACTERS_DATA)


# --- Intent roundtrip ---

INTENT_DATA = {
    "keep": ["父女对峙"],
    "no_delete": ["父亲之死"],
    "no_merge": ["林晚", "林父"],
    "must_keep_lines": ["原来你一直都……"],
    "mood_floor": "压抑",
    "allow_new_plot": False,
    "allow_reorder": True,
    "allow_new_ending": False,
    "target_type": "short_drama",
}


def test_intent_roundtrip() -> None:
    validate_roundtrip(IntentConstraints, INTENT_DATA)