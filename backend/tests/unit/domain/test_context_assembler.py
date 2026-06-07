"""Context assembler tests."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import HTTPException

from cardenio.domain.context_assembler import ContextAssembler
from cardenio.domain.models.base import ArtifactEnvelope, ArtifactState


class FakeStore:
    def __init__(self) -> None:
        self.project: dict[str, Any] | None = {
            "id": "proj_1",
            "style_fingerprint": "restrained; tense",
            "output_language": "zh-CN",
        }
        self.artifacts: dict[str, ArtifactEnvelope[Any]] = {}
        self.paragraphs: list[dict[str, Any]] = [
            {
                "project_id": "proj_1",
                "chapter_id": "ch_1",
                "paragraph_index": 1,
                "text": "Lin Wan opened the archive.",
            },
            {
                "project_id": "proj_1",
                "chapter_id": "ch_1",
                "paragraph_index": 2,
                "text": "Chen Mo watched her hide the letter.",
            },
        ]

    async def get_project(self, project_id: str) -> dict[str, Any] | None:
        return self.project if project_id == "proj_1" else None

    async def get_artifact(
        self,
        project_id: str,
        artifact_type: str,
    ) -> ArtifactEnvelope[Any] | None:
        if project_id != "proj_1":
            return None
        return self.artifacts.get(artifact_type)

    async def get_paragraphs(
        self,
        project_id: str,
        chapter_id: str | None = None,
    ) -> list[dict[str, Any]]:
        if project_id != "proj_1":
            return []
        return [
            paragraph
            for paragraph in self.paragraphs
            if chapter_id is None or paragraph["chapter_id"] == chapter_id
        ]


async def test_for_rewrite_builds_context_with_versions() -> None:
    store = FakeStore()
    store.artifacts = {
        "screenplay": _artifact("screenplay", "v_screenplay", _screenplay_data()),
        "characters": _artifact("characters", "v_characters", _characters_data()),
        "intent": _artifact("intent", "v_intent", _intent_data()),
        "understanding": _artifact("understanding", "v_understanding", _understanding_data()),
        "outline": _artifact("outline", "v_outline", _outline_data()),
    }

    bundle = await ContextAssembler(store=store).for_rewrite(
        "proj_1",
        "sc_001",
        "Bring the conflict forward.",
    )

    assert bundle.previous.version == "v_screenplay"
    assert bundle.target_index == 0
    assert bundle.target_scene.id == "sc_001"
    assert bundle.intent is not None
    assert bundle.understanding is not None
    assert bundle.outline is not None
    assert bundle.input_versions == {
        "screenplay": "v_screenplay",
        "characters": "v_characters",
        "intent": "v_intent",
        "understanding": "v_understanding",
        "outline": "v_outline",
    }

    context = bundle.context
    assert context.source_chunks == [
        {
            "type": "rewrite_request",
            "data": {
                "instruction": "Bring the conflict forward.",
                "scene_id": "sc_001",
            },
        }
    ]
    assert context.upstream_artifacts["target_scene"]["id"] == "sc_001"
    assert "next" in context.upstream_artifacts["adjacent_scenes"]
    assert context.upstream_artifacts["source_paragraphs"] == [
        {"index": 1, "text": "Lin Wan opened the archive."},
        {"index": 2, "text": "Chen Mo watched her hide the letter."},
    ]
    assert context.upstream_artifacts["character_voices"] == {
        "lin_wan": "Quiet, clipped.",
    }
    assert context.upstream_artifacts["author_intent"]["keep"] == ["sealed letter"]
    assert context.upstream_artifacts["understanding"]["style_fingerprint"] == (
        "restrained; tense"
    )
    assert context.system_constraints == {
        "style_fingerprint": "restrained; tense",
        "output_language": "zh-CN",
        "voice": {"lin_wan": "Quiet, clipped."},
        "hard_rules": [
            "All user-visible generated content must be written in Simplified Chinese."
        ],
        "author_intent": context.upstream_artifacts["author_intent"],
        "shot_hints_enabled": False,
    }


async def test_for_rewrite_missing_project_returns_404() -> None:
    store = FakeStore()
    store.project = None

    with pytest.raises(HTTPException) as exc_info:
        await ContextAssembler(store=store).for_rewrite(
            "proj_1",
            "sc_001",
            "Make it sharper.",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Project not found"


async def test_for_rewrite_missing_screenplay_returns_404() -> None:
    store = FakeStore()

    with pytest.raises(HTTPException) as exc_info:
        await ContextAssembler(store=store).for_rewrite(
            "proj_1",
            "sc_001",
            "Make it sharper.",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Screenplay not found"


async def test_for_rewrite_missing_scene_returns_404() -> None:
    store = FakeStore()
    store.artifacts = {
        "screenplay": _artifact("screenplay", "v_screenplay", _screenplay_data()),
    }

    with pytest.raises(HTTPException) as exc_info:
        await ContextAssembler(store=store).for_rewrite(
            "proj_1",
            "missing",
            "Make it sharper.",
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Scene not found"


def _artifact(
    artifact_type: str,
    version: str,
    data: dict[str, Any],
) -> ArtifactEnvelope[Any]:
    return ArtifactEnvelope(
        type=artifact_type,
        state=ArtifactState.DRAFT,
        version=version,
        data=data,
    )


def _screenplay_data() -> dict[str, Any]:
    return {
        "scenes": [
            {
                "id": "sc_001",
                "heading": {"int_ext": "INT", "location": "Archive", "time": "NIGHT"},
                "source_ref": {"chapter": 1, "paragraphs": [1, 2]},
                "synopsis": "Lin Wan confronts the hidden letter.",
                "goal": "Force the truth into the open.",
                "conflict": "Truth versus concealment.",
                "mood": "tense",
                "characters": ["lin_wan"],
                "foreshadowing": [],
                "relation_changes": [],
                "ending_state": "The letter is exposed.",
                "beats": [
                    {
                        "type": "action",
                        "text": "Lin Wan closes the archive door.",
                        "source_ref": {"chapter": 1, "paragraphs": [1, 2]},
                        "flag": "from_source",
                    }
                ],
            },
            {
                "id": "sc_002",
                "heading": {"int_ext": "EXT", "location": "Courtyard", "time": "DAWN"},
                "source_ref": {"chapter": 2, "paragraphs": [1]},
                "synopsis": "Chen Mo chooses silence.",
                "goal": "Avoid the consequence.",
                "conflict": "Silence versus confession.",
                "mood": "quiet",
                "characters": ["chen_mo"],
                "foreshadowing": [],
                "relation_changes": [],
                "ending_state": "He walks away.",
                "beats": [
                    {
                        "type": "action",
                        "text": "Chen Mo leaves before sunrise.",
                        "source_ref": {"chapter": 2, "paragraphs": [1]},
                        "flag": "from_source",
                    }
                ],
            },
        ],
        "shot_hints": {"enabled": False},
    }


def _characters_data() -> dict[str, Any]:
    return {
        "characters": [
            {
                "id": "lin_wan",
                "name": "Lin Wan",
                "role": "protagonist",
                "voice": "Quiet, clipped.",
                "desire": "Expose the truth.",
                "fear": "Being betrayed again.",
                "arc": "From avoidance to confrontation.",
                "relations": [],
                "hard_rules": [],
            }
        ]
    }


def _intent_data() -> dict[str, Any]:
    return {
        "keep": ["sealed letter"],
        "no_delete": [],
        "no_merge": [],
        "must_keep_lines": [],
        "mood_floor": "tense",
        "allow_new_plot": False,
        "allow_reorder": False,
        "allow_new_ending": False,
        "target_type": "short_drama",
    }


def _understanding_data() -> dict[str, Any]:
    return {
        "logline": "A sealed letter forces Lin Wan to confront Chen Mo.",
        "synopsis": "Archive secrets pull two characters into open conflict.",
        "themes": ["trust"],
        "protagonist_goal": "Expose the letter.",
        "protagonist_fear": "Losing the last bond.",
        "central_conflict": "Truth versus concealment.",
        "mood": "tense",
        "style_fingerprint": "restrained; tense",
        "narrative": {
            "perspective": "third_person_limited",
            "tense": "past",
            "unreliable": False,
        },
        "non_visualizable": [],
        "strengths": [],
        "difficulties": [],
    }


def _outline_data() -> dict[str, Any]:
    return {
        "scenes": [
            {
                "id": "sc_001",
                "heading": {"int_ext": "INT", "location": "Archive", "time": "NIGHT"},
                "source_ref": {"chapter": 1, "paragraphs": [1, 2]},
                "synopsis": "Lin Wan confronts the hidden letter.",
                "goal": "Force the truth into the open.",
                "conflict": "Truth versus concealment.",
                "mood": "tense",
                "characters": ["lin_wan"],
                "foreshadowing": [],
                "relation_changes": [],
                "ending_state": "The letter is exposed.",
            }
        ],
        "merge_suggestions": [],
    }
